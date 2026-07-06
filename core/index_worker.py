"""索引工作进程模块 (v2.5.0)

ProcessPoolExecutor 的 worker 必须是模块级函数 —— IndexerWorker 是 QObject，
无法跨进程 pickle，因此把"解析 + 分词"逻辑抽出到这里，由 indexer 进程池直接 submit。

设计要点：
- _init_worker: 每个 worker 进程启动时预加载 jieba 词典（并行，~0.5s）。
  词典缺失时 fail-fast（向上抛出 → 进程池 BrokenProcessPool → 主进程报错），
  避免静默产出空索引（用户以为索引成功却搜不到任何内容）。
- parse_and_tokenize: 返回 (stored_content, filename_tokens, content_tokens)。
  stored_content 截断到 MAX_CONTENT_CHARS(2M)，与分词搜索范围一致，零 snippet gap；
  截断后只回传 2M 内容，避免跨进程 IPC 回传整文件（大语料可达 GB 级）。
- worker 吞掉自身解析/分词异常并返回哨兵 _PARSE_ERROR，
  避免异常对象（可能携带不可 pickle 的成员）跨进程传播导致整批失败。
"""
from .text_utils import (
    clean_text,
    tokenize_content,
    tokenize_filename,
    get_jieba,
    MAX_CONTENT_CHARS,
)
from .parsers import parse_file

# 哨兵：worker 吞掉自身异常时返回，避免异常对象跨进程 pickle 失败
_PARSE_ERROR = ("", "", "")


def _init_worker():
    """ProcessPoolExecutor initializer：每个 worker 进程启动时预加载 jieba 词典。

    默认 jieba 在首次 cut() 时才懒加载词典；在此显式 initialize()：
      ① 并行预加载（多个 worker 同时加载，墙钟 ~0.5s）而非首文件串行；
      ② 词典缺失时立即失败（fail-fast），而非每个文件静默返回空内容。
    任何异常都向上抛出 → 进程池标记为 broken → 主进程捕获 BrokenProcessPool 报错。
    """
    jieba = get_jieba()
    if hasattr(jieba, "initialize"):
        jieba.initialize()


def parse_and_tokenize(filepath, ext, filename):
    """解析单个文件 + 分词（在 worker 进程中执行）。

    返回: (stored_content, filename_tokens, content_tokens)
      - stored_content: 截断到 MAX_CONTENT_CHARS(2M) 的文本，用于存储/预览/分词，
        搜索范围 == 存储范围 == snippet 范围，无 gap。
      - filename_tokens / content_tokens: 空格分隔的 token 字符串，供 FTS5 索引。

    解析或分词异常一律吞掉返回 _PARSE_ERROR，避免跨进程异常传播；
    主进程对哨兵按"空内容"处理（计入 error 统计由调用方决定）。
    """
    try:
        text, _ = parse_file(filepath, ext)
        text = clean_text(text)
    except Exception:
        return _PARSE_ERROR

    # 截断一次：存储 / 分词共用同一段，搜索范围 == snippet 范围 == 预览范围
    if len(text) > MAX_CONTENT_CHARS:
        text = text[:MAX_CONTENT_CHARS]

    try:
        fn_tok = tokenize_filename(filename)
        c_tok = tokenize_content(text) if text else ""
    except Exception:
        return _PARSE_ERROR

    return text, fn_tok, c_tok
