"""搜索引擎 - 全文搜索、模糊搜索、结果排序"""
import os
import time
from .database import IndexDatabase
from .text_utils import (
    prepare_search_query, tokenize_chinese, highlight_text,
    format_file_size, decode_bytes
)


class SearchResult:
    """搜索结果项"""

    def __init__(self, file_id, relative_path, filename, extension,
                 file_size, modified_time, content, is_valid, rank=0):
        self.file_id = file_id
        self.relative_path = relative_path
        self.filename = filename
        self.extension = extension
        self.file_size = file_size
        self.modified_time = modified_time
        self.content = content or ""
        self.is_valid = is_valid
        self.rank = rank

    @property
    def file_size_str(self):
        return format_file_size(self.file_size)

    @property
    def modified_time_str(self):
        try:
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.modified_time))
        except (OSError, ValueError):
            return "未知"

    @property
    def is_available(self):
        """文件是否可用（硬盘是否连接）"""
        return self.is_valid == 1

    def get_snippets(self, keywords, context_chars=80):
        """获取关键词高亮片段"""
        if not self.content:
            return []
        return highlight_text(self.content, keywords, context_chars)


class SearchEngine:
    """搜索引擎"""

    def __init__(self):
        self.databases = []  # 已加载的索引数据库列表
        self.db_labels = {}  # db_path -> 标签名

    def load_index(self, db_path, label=None):
        """加载索引文件"""
        db = IndexDatabase()
        db.open(db_path)
        self.databases.append(db)
        if label:
            self.db_labels[db_path] = label
        return db

    def unload_index(self, db_path):
        """卸载索引文件"""
        self.databases = [db for db in self.databases if db.db_path != db_path]
        if db_path in self.db_labels:
            del self.db_labels[db_path]

    def unload_all(self):
        """卸载所有索引"""
        for db in self.databases:
            db.close()
        self.databases = []
        self.db_labels = {}

    def get_loaded_indexes(self):
        """获取已加载的索引列表"""
        result = []
        for db in self.databases:
            label = self.db_labels.get(db.db_path, os.path.basename(db.db_path))
            root_path = db.get_root_path()
            stats = db.get_statistics()
            result.append({
                "path": db.db_path,
                "label": label,
                "root_path": root_path,
                "total_files": stats.get("total_files", 0),
                "index_size": stats.get("index_size", 0),
                "last_index_time": stats.get("last_index_time", 0),
            })
        return result

    def search(self, query, limit=500, sort_by="relevance"):
        """执行搜索
        query: 搜索关键词
        limit: 最大结果数
        sort_by: relevance / time / size / name
        返回: list of SearchResult
        """
        if not self.databases:
            return []

        query = query.strip()
        if not query:
            return self._get_all_files(limit, sort_by)

        # 判断搜索类型
        is_fuzzy, processed_query = prepare_search_query(query)

        all_results = []

        for db in self.databases:
            if is_fuzzy:
                # 模糊搜索 - 使用LIKE
                rows = db.search_like(processed_query, limit)
            else:
                # 精确搜索 - 使用FTS5
                rows = db.search_fts(processed_query, limit)

                # 如果FTS没结果，回退到LIKE
                if not rows:
                    rows = db.search_like(query, limit)

            for row in rows:
                result = SearchResult(*row[:8])
                all_results.append(result)

        # 排序
        all_results = self._sort_results(all_results, sort_by)

        # 去重（按文件路径）
        seen = set()
        unique_results = []
        for r in all_results:
            key = (r.relative_path, r.filename)
            if key not in seen:
                seen.add(key)
                unique_results.append(r)

        return unique_results[:limit]

    def _get_all_files(self, limit, sort_by):
        """获取所有文件（空搜索时）"""
        all_results = []
        for db in self.databases:
            rows = db.get_all_files(limit)
            for row in rows:
                result = SearchResult(*row[:8])
                all_results.append(result)
        return self._sort_results(all_results, sort_by)[:limit]

    def _sort_results(self, results, sort_by):
        """排序结果"""
        if sort_by == "time":
            results.sort(key=lambda r: r.modified_time, reverse=True)
        elif sort_by == "size":
            results.sort(key=lambda r: r.file_size, reverse=True)
        elif sort_by == "name":
            results.sort(key=lambda r: r.filename.lower())
        else:  # relevance
            results.sort(key=lambda r: r.rank)
        return results

    def get_file_content(self, file_id):
        """获取文件内容（离线查看）"""
        for db in self.databases:
            content = db.get_file_content(file_id)
            if content:
                return content
        return ""

    def get_file_by_id(self, file_id):
        """根据ID获取文件信息（内容从FTS表获取）"""
        for db in self.databases:
            row = db.get_file_by_id(file_id)
            if row:
                # row: (id, relative_path, filename, extension, file_size, modified_time, is_valid)
                content = db.get_file_content(file_id)
                return SearchResult(row[0], row[1], row[2], row[3], row[4], row[5], content, row[6])
        return None

    def get_full_path(self, result):
        """获取文件的完整路径（结合当前根路径）"""
        for db in self.databases:
            if db.db_path:
                root = db.get_root_path()
                if root:
                    return os.path.join(root, result.relative_path)
        return result.relative_path

    def close(self):
        """关闭所有数据库"""
        self.unload_all()
