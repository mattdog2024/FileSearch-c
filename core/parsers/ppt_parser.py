"""PPT/PPTX 文件解析器"""


def parse_pptx(filepath):
    """解析 .pptx 文件（Office Open XML格式）"""
    try:
        from pptx import Presentation
        prs = Presentation(filepath)
        text_parts = []

        for slide_num, slide in enumerate(prs.slides, 1):
            slide_texts = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            slide_texts.append(text)

                if shape.has_table:
                    for row in shape.table.rows:
                        cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                        if cells:
                            slide_texts.append(" | ".join(cells))

            if slide_texts:
                text_parts.append(f"[幻灯片 {slide_num}]")
                text_parts.extend(slide_texts)

        # 也提取备注
        for slide_num, slide in enumerate(prs.slides, 1):
            if slide.has_notes_slide:
                notes = slide.notes_slide.notes_text_frame.text.strip()
                if notes:
                    text_parts.append(f"[备注 {slide_num}] {notes}")

        return "\n".join(text_parts)
    except ImportError:
        raise RuntimeError("python-pptx 未安装")
    except Exception as e:
        raise RuntimeError(f"PPTX解析失败: {e}")


def parse_ppt(filepath):
    """解析 .ppt 文件（旧版OLE格式）"""
    # 方法1: 使用 olefile 提取
    text = _parse_ppt_olefile(filepath)
    if text and len(text.strip()) > 50:
        return text

    # 方法2: 二进制提取
    text = _parse_ppt_binary(filepath)
    return text or ""


def _parse_ppt_olefile(filepath):
    """使用olefile解析.ppt文件"""
    try:
        import olefile
        if not olefile.isOleFile(filepath):
            return ""

        ole = olefile.OleFileIO(filepath)
        text_parts = []

        # PowerPoint 文档的主要流
        for stream_name in ["PowerPoint Document", "Current User"]:
            if ole.exists(stream_name):
                stream = ole.openstream(stream_name)
                data = stream.read()
                stream.close()

                text = _extract_ppt_strings(data)
                if text:
                    text_parts.append(text)

        ole.close()
        return "\n".join(text_parts)
    except ImportError:
        return ""
    except Exception:
        return ""


def _extract_ppt_strings(data):
    """从PPT二进制数据中提取字符串"""
    text_parts = []
    i = 0

    while i < len(data) - 1:
        code = data[i] | (data[i + 1] << 8)

        if 0x20 <= code < 0xFFFE:
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


def _parse_ppt_binary(filepath):
    """从二进制.ppt文件中提取文本"""
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

        raw = "\n".join(text_parts)
        try:
            from core.text_utils import decode_bytes
            return decode_bytes(raw.encode("latin-1"))
        except Exception:
            return raw
    except Exception:
        return ""
