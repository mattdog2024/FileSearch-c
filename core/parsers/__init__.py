"""文件解析器包"""
from .doc_parser import parse_doc, parse_docx
from .pdf_parser import parse_pdf
from .xls_parser import parse_xls, parse_xlsx
from .ppt_parser import parse_ppt, parse_pptx


# 支持的格式与对应解析函数
PARSERS = {
    ".doc": parse_doc,
    ".docx": parse_docx,
    ".xls": parse_xls,
    ".xlsx": parse_xlsx,
    ".pdf": parse_pdf,
    ".ppt": parse_ppt,
    ".pptx": parse_pptx,
}


def parse_file(filepath, extension=None):
    """根据文件扩展名选择合适的解析器
    返回: (text_content, error_msg)
    """
    import os
    if extension is None:
        extension = os.path.splitext(filepath)[1].lower()

    parser = PARSERS.get(extension)
    if parser is None:
        return "", f"不支持的文件格式: {extension}"

    try:
        text = parser(filepath)
        return text or "", ""
    except Exception as e:
        return "", str(e)


def get_supported_extensions():
    """获取所有支持的扩展名列表"""
    return list(PARSERS.keys())
