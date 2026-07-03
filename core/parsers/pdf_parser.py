"""PDF 文件解析器 - 优化版（PyPDF2优先，速度更快）"""


def parse_pdf(filepath):
    """解析 PDF 文件，提取全文文本
    优化策略：先用 PyPDF2（快），失败/空结果再用 pdfplumber（慢但准确）
    """
    # 优先使用 PyPDF2（速度快10倍以上）
    try:
        text = _parse_with_pypdf2(filepath)
        if text and len(text.strip()) > 50:
            return text
    except ImportError:
        pass
    except Exception:
        pass

    # PyPDF2 结果为空或失败时，回退到 pdfplumber
    try:
        return _parse_with_pdfplumber(filepath)
    except ImportError:
        pass
    except Exception:
        pass

    # 最后一次尝试 PyPDF2（即使结果少）
    try:
        return _parse_with_pypdf2(filepath)
    except ImportError:
        raise RuntimeError("PDF解析库未安装（需要 pdfplumber 或 PyPDF2）")
    except Exception as e:
        raise RuntimeError(f"PDF解析失败: {e}")


def _parse_with_pypdf2(filepath):
    """使用 PyPDF2 解析 PDF（速度快）"""
    from PyPDF2 import PdfReader

    reader = PdfReader(filepath)
    text_parts = []

    for page in reader.pages:
        try:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        except Exception:
            continue

    return "\n".join(text_parts)


def _parse_with_pdfplumber(filepath):
    """使用 pdfplumber 解析 PDF（慢但准确，作为后备）"""
    import pdfplumber

    text_parts = []
    with pdfplumber.open(filepath) as pdf:
        for i, page in enumerate(pdf.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

                # 也提取表格
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            cells = [str(cell).strip() for cell in row if cell]
                            if cells:
                                text_parts.append(" ".join(cells))
            except Exception:
                continue  # 跳过有问题的页面

    return "\n".join(text_parts)
