"""XLS/XLSX 文件解析器"""


def parse_xlsx(filepath):
    """解析 .xlsx 文件（Office Open XML格式）"""
    try:
        from openpyxl import load_workbook
        wb = load_workbook(filepath, read_only=True, data_only=True)
        text_parts = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            text_parts.append(f"[工作表: {sheet_name}]")

            for row in ws.iter_rows(values_only=True):
                cells = []
                for cell in row:
                    if cell is not None:
                        cells.append(str(cell))
                if cells:
                    text_parts.append(" | ".join(cells))

        wb.close()
        return "\n".join(text_parts)
    except ImportError:
        raise RuntimeError("openpyxl 未安装")
    except Exception as e:
        raise RuntimeError(f"XLSX解析失败: {e}")


def parse_xls(filepath):
    """解析 .xls 文件（旧版OLE格式）"""
    # 方法1: 使用 olefile 提取
    text = _parse_xls_olefile(filepath)
    if text and len(text.strip()) > 50:
        return text

    # 方法2: 二进制提取
    text = _parse_xls_binary(filepath)
    return text or ""


def _parse_xls_olefile(filepath):
    """使用olefile解析.xls文件"""
    try:
        import olefile
        if not olefile.isOleFile(filepath):
            return ""

        ole = olefile.OleFileIO(filepath)
        text_parts = []

        # Workbook 流包含主要数据
        if ole.exists("Workbook"):
            stream = ole.openstream("Workbook")
            data = stream.read()
            stream.close()

            # 提取字符串（Unicode和ASCII）
            text = _extract_xls_strings(data)
            if text:
                text_parts.append(text)

        ole.close()
        return "\n".join(text_parts)
    except ImportError:
        return ""
    except Exception:
        return ""


def _extract_xls_strings(data):
    """从XLS二进制数据中提取字符串"""
    text_parts = []
    i = 0

    while i < len(data) - 1:
        # 查找 UTF-16LE 字符串段
        code = data[i] | (data[i + 1] << 8)

        if 0x20 <= code < 0xFFFE:
            # 可能是字符串开始
            start = i
            chars = []
            while i < len(data) - 1:
                code = data[i] | (data[i + 1] << 8)
                if 0x20 <= code < 0xFFFE:
                    chars.append(chr(code))
                    i += 2
                else:
                    break

            if len(chars) >= 3:
                text_parts.append("".join(chars))
        else:
            i += 1

    return "\n".join(text_parts)


def _parse_xls_binary(filepath):
    """从二进制.xls文件中提取文本"""
    try:
        with open(filepath, "rb") as f:
            data = f.read()

        text_parts = []
        current = []

        for byte in data:
            if 0x20 <= byte < 0x7F:
                current.append(chr(byte))
            elif 0x80 <= byte <= 0xFE:
                current.append(chr(byte))
            else:
                if len(current) > 4:
                    text_parts.append("".join(current))
                current = []

        if len(current) > 4:
            text_parts.append("".join(current))

        # 尝试GBK解码
        raw = "\n".join(text_parts)
        try:
            from core.text_utils import decode_bytes
            return decode_bytes(raw.encode("latin-1"))
        except Exception:
            return raw
    except Exception:
        return ""
