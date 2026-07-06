"""文件解析器包"""
from .doc_parser import parse_doc, parse_docx
from .pdf_parser import parse_pdf
from .xls_parser import parse_xls, parse_xlsx
from .ppt_parser import parse_ppt, parse_pptx
from .text_parser import parse_txt, parse_md, parse_code


# 支持的格式与对应解析函数
PARSERS = {
    # Office 文档
    ".doc": parse_doc,
    ".docx": parse_docx,
    ".xls": parse_xls,
    ".xlsx": parse_xlsx,
    ".ppt": parse_ppt,
    ".pptx": parse_pptx,
    ".pdf": parse_pdf,
    # 纯文本 / Markdown
    ".txt": parse_txt,
    ".log": parse_txt,
    ".md": parse_md,
    # 代码（对齐 ui/main_window.py 的 TYPE_CATEGORY_MAP 'code' 分类）
    ".py": parse_code,
    ".js": parse_code,
    ".ts": parse_code,
    ".java": parse_code,
    ".c": parse_code,
    ".cpp": parse_code,
    ".h": parse_code,
    ".css": parse_code,
    ".html": parse_code,
    ".htm": parse_code,
    ".json": parse_code,
    ".xml": parse_code,
    ".yaml": parse_code,
    ".sql": parse_code,
    ".sh": parse_code,
    ".bat": parse_code,
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
