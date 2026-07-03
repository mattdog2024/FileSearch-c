"""文本工具模块 - 编码检测、中文分词、文本清洗（性能优化版）
- chardet 只读前 8KB
- jieba 分词用于索引和搜索
"""
import re
import os

# jieba 延迟加载
_jieba = None
_jieba_loaded = False


def get_jieba():
    """获取jieba分词器（延迟加载）"""
    global _jieba, _jieba_loaded
    if not _jieba_loaded:
        import jieba
        # 减少 jieba 日志输出
        jieba.setLogLevel(20)
        _jieba = jieba
        _jieba_loaded = True
    return _jieba


def detect_encoding(file_path, sample_size=8192):
    """检测文件的编码（只读前 8KB，大幅减少 I/O）"""
    import chardet
    try:
        with open(file_path, 'rb') as f:
            raw = f.read(sample_size)
        if not raw:
            return 'utf-8'
        result = chardet.detect(raw)
        encoding = result.get("encoding", "utf-8")
        if encoding is None:
            encoding = "utf-8"
        return encoding.lower()
    except (OSError, IOError):
        return 'utf-8'


def decode_bytes(raw_bytes, encoding=None):
    """将字节流解码为字符串，自动检测编码"""
    if encoding is None:
        import chardet
        # 只取前 8KB 检测编码
        sample = raw_bytes[:8192] if len(raw_bytes) > 8192 else raw_bytes
        result = chardet.detect(sample)
        encoding = result.get("encoding", "utf-8")
        if encoding is None:
            encoding = "utf-8"

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


def tokenize_content(text):
    """对文件内容进行分词（用于FTS5索引）
    - 中文用 jieba 分词
    - 英文保留原词
    - 返回空格分隔的 token 字符串
    """
    if not text:
        return ""
    jieba = get_jieba()
    words = jieba.cut_for_search(text)
    # 过滤空白，保留长度 >= 1 的词
    tokens = [w.strip() for w in words if w.strip()]
    return " ".join(tokens)


def tokenize_filename(text):
    """对文件名进行分词"""
    if not text:
        return ""
    jieba = get_jieba()
    words = jieba.cut(text, HMM=False)
    tokens = [w.strip() for w in words if w.strip()]
    return " ".join(tokens)


def prepare_search_query(query):
    """准备搜索查询
    返回: (is_fuzzy, processed_query)
    - is_fuzzy: 是否包含通配符
    - processed_query: 处理后的查询字符串

    中文搜索用 jieba 分词 + FTS5 OR 匹配
    """
    query = query.strip()
    if not query:
        return False, ""

    # 检查是否包含通配符
    has_wildcard = "*" in query or "?" in query
    if has_wildcard:
        return True, query

    # 检查是否是引号包裹的精确搜索
    if query.startswith('"') and query.endswith('"'):
        inner = query[1:-1].strip()
        if not inner:
            return False, ""
        # 精确短语搜索 - 用 NEAR 连接每个 token
        jieba = get_jieba()
        words = [w.strip() for w in jieba.cut(inner) if w.strip()]
        if words:
            return False, " NEAR ".join(words)
        return False, f'"{inner}"'

    # 普通搜索 - 用 jieba 分词
    jieba = get_jieba()
    # 按空格分割用户输入的多关键词
    parts = query.split()
    all_tokens = []
    for part in parts:
        words = [w.strip() for w in jieba.cut(part) if w.strip()]
        all_tokens.extend(words)

    if not all_tokens:
        return False, ""

    # 去重
    seen = set()
    unique_tokens = []
    for t in all_tokens:
        if t not in seen:
            seen.add(t)
            unique_tokens.append(t)

    # FTS5 查询：用 OR 连接所有 token
    if len(unique_tokens) == 1:
        return False, unique_tokens[0]
    return False, " OR ".join(unique_tokens)


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
