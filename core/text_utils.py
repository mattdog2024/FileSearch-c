"""文本工具模块 - 编码检测、中文分词、文本清洗"""
import re
import chardet


def detect_encoding(raw_bytes):
    """检测字节流的编码"""
    result = chardet.detect(raw_bytes)
    encoding = result.get("encoding", "utf-8")
    if encoding is None:
        encoding = "utf-8"
    return encoding.lower()


def decode_bytes(raw_bytes, encoding=None):
    """将字节流解码为字符串，自动检测编码"""
    if encoding is None:
        encoding = detect_encoding(raw_bytes)

    # 常见中文编码映射
    encoding_map = {
        "gb2312": "gbk",
        "ascii": "utf-8",
        "iso-8859-1": "gbk",  # 可能是误检
    }
    encoding = encoding_map.get(encoding, encoding)

    try:
        return raw_bytes.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        # 回退策略
        for enc in ["utf-8", "gbk", "gb18030", "big5", "latin-1"]:
            try:
                return raw_bytes.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw_bytes.decode("utf-8", errors="replace")


def clean_text(text):
    """清洗文本：去除多余空白、控制字符"""
    if not text:
        return ""
    # 去除控制字符（保留换行和制表符）
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # 合并多个空白为单个空格（保留换行）
    text = re.sub(r'[^\S\n]+', ' ', text)
    # 合并多个换行为双换行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# jieba 延迟加载
_jieba = None
_jieba_loaded = False


def get_jieba():
    """获取jieba分词器（延迟加载）"""
    global _jieba, _jieba_loaded
    if not _jieba_loaded:
        import jieba
        _jieba = jieba
        _jieba_loaded = True
    return _jieba


def tokenize_chinese(text):
    """使用jieba对中文文本进行分词，返回空格分隔的分词结果"""
    if not text:
        return ""
    jieba = get_jieba()
    # 分词
    words = jieba.cut_for_search(text)
    # 过滤掉单字符和空白
    tokens = [w.strip() for w in words if w.strip() and len(w.strip()) > 1]
    return " ".join(tokens)


def tokenize_filename(text):
    """对文件名进行分词（更细粒度）"""
    if not text:
        return ""
    jieba = get_jieba()
    words = jieba.cut(text, HMM=False)
    tokens = [w.strip() for w in words if w.strip() and len(w.strip()) > 0]
    return " ".join(tokens)


def prepare_search_query(query):
    """准备搜索查询
    返回: (is_fuzzy, processed_query)
    - is_fuzzy: 是否包含通配符
    - processed_query: 处理后的查询字符串

    注意：FTS5使用unicode61分词器，中文按字符切分
    所以查询词也需要按字符切分来匹配
    """
    query = query.strip()

    # 检查是否包含通配符
    has_wildcard = "*" in query or "?" in query

    if has_wildcard:
        return True, query

    # 检查是否是引号包裹的精确搜索
    if query.startswith('"') and query.endswith('"'):
        inner = query[1:-1]
        # 精确短语搜索 - 用NEAR连接字符
        chars = list(inner.replace(" ", ""))
        if chars:
            return False, " NEAR ".join(chars)
        return False, f'"{inner}"'

    # 普通搜索 - 按字符切分（匹配unicode61分词）
    # 移除空格，将中文查询词拆成单字符
    clean_query = query.replace(" ", "")
    if clean_query:
        # 将每个字符用AND连接，确保所有字符都匹配
        chars = list(clean_query)
        if len(chars) > 1:
            return False, " AND ".join(chars)
        return False, clean_query

    return False, query


def highlight_text(text, keywords, context_chars=80):
    """在文本中高亮关键词，返回带标记的文本片段列表
    返回: [(snippet, [(start, end), ...]), ...]
    """
    if not text or not keywords:
        return [(text[:200] if text else "", [])]

    text_lower = text.lower()
    keyword_list = [k.lower() for k in keywords if k]

    if not keyword_list:
        return [(text[:200] if text else "", [])]

    # 找到所有匹配位置
    matches = []
    for kw in keyword_list:
        start = 0
        while True:
            pos = text_lower.find(kw, start)
            if pos == -1:
                break
            matches.append((pos, pos + len(kw)))
            start = pos + 1

    if not matches:
        # 没有匹配，返回开头
        return [(text[:context_chars * 2], [])]

    # 合并重叠区间
    matches.sort()
    merged = [matches[0]]
    for s, e in matches[1:]:
        if s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))

    # 生成带上下文的片段
    snippets = []
    for match_start, match_end in merged:
        ctx_start = max(0, match_start - context_chars)
        ctx_end = min(len(text), match_end + context_chars)

        # 调整到词边界
        if ctx_start > 0:
            while ctx_start > max(0, match_start - context_chars - 10) and text[ctx_start] not in " \n。！？；：，、":
                ctx_start -= 1
        if ctx_end < len(text):
            while ctx_end < min(len(text), match_end + context_chars + 10) and text[ctx_end] not in " \n。！？；：，、":
                ctx_end += 1

        snippet = text[ctx_start:ctx_end]
        # 计算片段内的匹配位置
        snippet_matches = []
        for ms, me in merged:
            if ms >= ctx_start and me <= ctx_end:
                snippet_matches.append((ms - ctx_start, me - ctx_start))

        prefix = "..." if ctx_start > 0 else ""
        suffix = "..." if ctx_end < len(text) else ""
        snippets.append((prefix + snippet + suffix, snippet_matches))

        if len(snippets) >= 5:  # 最多5个片段
            break

    return snippets


def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
