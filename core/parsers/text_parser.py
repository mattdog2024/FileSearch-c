"""TXT / Markdown / 代码 文件解析器

这些纯文本类型共用同一套读取逻辑：读字节 → decode_bytes 自动检测编码
（GBK/UTF-8/Big5/...）→ 返回字符串。控制字符与空白合并等清洗由 index_worker 的
clean_text 统一完成，此处不重复，避免对同一份文本跑两遍正则替换。
"""
from ..text_utils import decode_bytes

# 单个纯文本文件最大读取字节数。超大文本（如导出的日志/数据 dump）只读前若干 MB，
# 解码后由 worker 截断到 MAX_CONTENT_CHARS(2M 字符)，存储范围 == 搜索范围，避免
# 无谓的整文件读取与解码开销。6MB 字节 → 解码后约 2-6M 字符，足够覆盖。
_MAX_TEXT_BYTES = 6 * 1024 * 1024


def _read_text(filepath):
    """读取纯文本文件的通用逻辑：读字节 → 自动检测编码解码。"""
    try:
        with open(filepath, "rb") as f:
            raw = f.read(_MAX_TEXT_BYTES)
        if not raw:
            return ""
        return decode_bytes(raw)
    except Exception:
        return ""


def parse_txt(filepath):
    """解析 .txt/.log 等纯文本文件"""
    return _read_text(filepath)


def parse_md(filepath):
    """解析 Markdown 文件

    与 txt 共用读取逻辑；保留 markdown 标记符号（#、*、`、[] 等）——它们本身可被搜索，
    剥离反而可能丢失用户想定位的代码片段或标题文本。后续清洗由 clean_text 统一处理。
    """
    return _read_text(filepath)


def parse_code(filepath):
    """解析代码文件（.py/.js/.json/.xml/...）——本质即纯文本"""
    return _read_text(filepath)
