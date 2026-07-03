"""DOC/DOCX 文件解析器"""
import os
import struct
import re


def parse_docx(filepath):
    """解析 .docx 文件（Office Open XML格式）"""
    try:
        from docx import Document
        doc = Document(filepath)
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)

        # 也提取表格中的文本
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text = cell.text.strip()
                    if text:
                        paragraphs.append(text)

        return "\n".join(paragraphs)
    except ImportError:
        raise RuntimeError("python-docx 未安装")
    except Exception as e:
        raise RuntimeError(f"DOCX解析失败: {e}")


def parse_doc(filepath):
    """解析 .doc 文件（旧版OLE格式）
    使用多种方法尝试提取文本
    """
    # 方法1: 使用 olefile 提取 OLE 流
    text = _parse_doc_olefile(filepath)
    if text and len(text.strip()) > 50:
        return text

    # 方法2: 从二进制中直接提取可读文本
    text = _parse_doc_binary(filepath)
    if text and len(text.strip()) > 50:
        return text

    return ""


def _parse_doc_olefile(filepath):
    """使用olefile解析.doc文件"""
    try:
        import olefile
        if not olefile.isOleFile(filepath):
            return ""

        ole = olefile.OleFileIO(filepath)

        # Word文档的主要文本流
        text_parts = []

        # 尝试从 WordDocument 流提取
        if ole.exists("WordDocument"):
            stream = ole.openstream("WordDocument")
            data = stream.read()
            stream.close()

            # 尝试提取 Unicode 文本
            text = _extract_unicode_text(data)
            if text:
                text_parts.append(text)

        # 尝试从 1Table 或 0Table 流获取补充信息
        for table_name in ["1Table", "0Table"]:
            if ole.exists(table_name):
                stream = ole.openstream(table_name)
                data = stream.read()
                stream.close()
                text = _extract_unicode_text(data)
                if text and len(text) > 20:
                    text_parts.append(text)

        ole.close()

        combined = "\n".join(text_parts)
        return _clean_doc_text(combined)

    except ImportError:
        return ""
    except Exception:
        return ""


def _parse_doc_binary(filepath):
    """从二进制.doc文件中直接提取可读文本"""
    try:
        with open(filepath, "rb") as f:
            data = f.read()

        # 提取 UTF-16LE 文本段
        text = _extract_unicode_text(data)
        if text and len(text.strip()) > 50:
            return _clean_doc_text(text)

        # 提取 ASCII/GBK 文本段
        text = _extract_ascii_text(data)
        if text and len(text.strip()) > 50:
            return _clean_doc_text(text)

        return ""
    except Exception:
        return ""


def _extract_unicode_text(data):
    """从二进制数据中提取UTF-16LE编码的文本"""
    text_parts = []
    i = 0
    current = []

    while i < len(data) - 1:
        # 读取 UTF-16LE 字符
        code = data[i] | (data[i + 1] << 8)

        if 0x20 <= code < 0xFFFE or code in (0x0A, 0x0D, 0x09):
            try:
                char = chr(code)
                current.append(char)
            except (ValueError, OverflowError):
                if len(current) > 3:
                    text_parts.append("".join(current))
                current = []
        else:
            if len(current) > 3:
                text_parts.append("".join(current))
            current = []
        i += 2

    if len(current) > 3:
        text_parts.append("".join(current))

    return "\n".join(text_parts)


def _extract_ascii_text(data):
    """从二进制数据中提取ASCII/GBK文本"""
    text_parts = []
    current = []

    for byte in data:
        if 0x20 <= byte < 0x7F or byte in (0x0A, 0x0D, 0x09):
            current.append(chr(byte))
        elif 0x80 <= byte <= 0xFE:
            # 可能是GBK高字节
            current.append(chr(byte))
        else:
            if len(current) > 5:
                text_parts.append("".join(current))
            current = []

    if len(current) > 5:
        text_parts.append("".join(current))

    # 尝试用GBK解码
    raw = "\n".join(text_parts)
    try:
        from .text_utils import decode_bytes
        return decode_bytes(raw.encode("latin-1"))
    except Exception:
        return raw


def _clean_doc_text(text):
    """清理从doc提取的文本"""
    if not text:
        return ""
    # 去除连续空字符
    text = re.sub(r'\x00+', '', text)
    # 去除控制字符
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    # 合并多个空白
    text = re.sub(r' {2,}', ' ', text)
    # 合并多个换行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
