"""数据库操作模块 - SQLite + FTS5 全文索引"""
import sqlite3
import os
import json
import time
from contextlib import contextmanager


class IndexDatabase:
    """索引数据库管理"""

    def __init__(self, db_path=None):
        self.db_path = db_path
        self.conn = None

    def create(self, db_path):
        """创建新索引数据库"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._create_tables()
        return self

    def open(self, db_path):
        """打开已有索引数据库"""
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"索引文件不存在: {db_path}")
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        return self

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        try:
            self.conn.execute("BEGIN")
            yield
            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def _create_tables(self):
        """创建数据表（不存content，内容只在FTS表中，减少数据库大小）"""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                relative_path TEXT NOT NULL,
                filename TEXT NOT NULL,
                extension TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                modified_time REAL NOT NULL,
                is_valid INTEGER DEFAULT 1,
                index_time REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS index_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_files_path ON files(relative_path);
            CREATE INDEX IF NOT EXISTS idx_files_ext ON files(extension);
            CREATE INDEX IF NOT EXISTS idx_files_valid ON files(is_valid);
        """)
        self.conn.commit()

    def create_fts_table(self):
        """创建FTS5全文搜索表（独立存储，不依赖files表的内容列）"""
        self.conn.executescript("""
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                filename,
                content,
                tokenize='unicode61'
            );
        """)
        self.conn.commit()

    # ---- 元数据操作 ----

    def set_meta(self, key, value):
        """设置索引元数据"""
        self.conn.execute(
            "INSERT OR REPLACE INTO index_meta (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        self.conn.commit()

    def get_meta(self, key, default=None):
        """获取索引元数据"""
        row = self.conn.execute(
            "SELECT value FROM index_meta WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else default

    def set_root_path(self, path):
        """设置索引的根路径"""
        self.set_meta("root_path", path)

    def get_root_path(self):
        """获取索引的根路径"""
        return self.get_meta("root_path", "")

    def set_file_types(self, types_list):
        """设置索引的文件类型"""
        self.set_meta("file_types", json.dumps(types_list, ensure_ascii=False))

    def get_file_types(self):
        """获取索引的文件类型"""
        val = self.get_meta("file_types", "[]")
        return json.loads(val)

    def set_last_index_time(self, t=None):
        """设置最后索引时间"""
        self.set_meta("last_index_time", str(t or time.time()))

    def get_last_index_time(self):
        """获取最后索引时间"""
        val = self.get_meta("last_index_time", "0")
        return float(val)

    # ---- 文件记录操作 ----

    def get_file_by_path(self, relative_path):
        """根据相对路径获取文件记录"""
        row = self.conn.execute(
            "SELECT id, file_size, modified_time, is_valid FROM files WHERE relative_path = ?",
            (relative_path,)
        ).fetchone()
        return row

    def insert_file(self, relative_path, filename, extension, file_size,
                    modified_time, index_time=None):
        """插入文件记录（不含content，内容存FTS表）"""
        if index_time is None:
            index_time = time.time()
        cursor = self.conn.execute(
            """INSERT INTO files
               (relative_path, filename, extension, file_size, modified_time, index_time)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (relative_path, filename, extension.lower(), file_size,
             modified_time, index_time)
        )
        return cursor.lastrowid

    def update_file(self, file_id, file_size, modified_time, index_time=None):
        """更新文件记录（不含content）"""
        if index_time is None:
            index_time = time.time()
        self.conn.execute(
            """UPDATE files SET file_size=?, modified_time=?, index_time=?, is_valid=1
               WHERE id=?""",
            (file_size, modified_time, index_time, file_id)
        )

    def mark_invalid(self, file_id):
        """标记文件为无效（已删除）"""
        self.conn.execute(
            "UPDATE files SET is_valid=0 WHERE id=?", (file_id,)
        )

    def mark_all_invalid(self):
        """标记所有文件为无效（重新索引前调用）"""
        self.conn.execute("UPDATE files SET is_valid=0")
        self.conn.commit()

    def get_all_indexed_paths(self):
        """获取所有已索引的有效文件路径"""
        rows = self.conn.execute(
            "SELECT relative_path, file_size, modified_time FROM files WHERE is_valid=1"
        ).fetchall()
        return {row[0]: (row[1], row[2]) for row in rows}

    # ---- FTS操作 ----

    def insert_fts(self, rowid, filename_tokens, content_tokens):
        """插入FTS记录（已分词）"""
        self.conn.execute(
            "INSERT INTO files_fts (rowid, filename, content) VALUES (?, ?, ?)",
            (rowid, filename_tokens, content_tokens)
        )

    def delete_fts(self, rowid):
        """删除FTS记录"""
        try:
            self.conn.execute(
                "DELETE FROM files_fts WHERE rowid=?", (rowid,)
            )
        except sqlite3.OperationalError:
            pass  # FTS表可能不存在

    # ---- 搜索操作 ----

    def search_fts(self, query, limit=500):
        """FTS5全文搜索（独立FTS表，内容从FTS获取）"""
        try:
            rows = self.conn.execute(
                """SELECT f.id, f.relative_path, f.filename, f.extension,
                          f.file_size, f.modified_time, fts.content, f.is_valid,
                          rank
                   FROM files_fts fts
                   JOIN files f ON f.id = fts.rowid
                   WHERE files_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (query, limit)
            ).fetchall()
            return rows
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                return []
            raise

    def search_like(self, keyword, limit=500):
        """LIKE模糊搜索（用于通配符查询，仅搜文件名）"""
        pattern = keyword.replace("*", "%").replace("?", "_")
        if not pattern.startswith("%"):
            pattern = "%" + pattern
        if not pattern.endswith("%"):
            pattern = pattern + "%"

        rows = self.conn.execute(
            """SELECT id, relative_path, filename, extension,
                      file_size, modified_time, '', is_valid, 0 as rank
               FROM files
               WHERE filename LIKE ? AND is_valid=1
               LIMIT ?""",
            (pattern, limit)
        ).fetchall()
        return rows

    def search_filename_like(self, keyword, limit=500):
        """文件名模糊搜索"""
        pattern = "%" + keyword.replace("*", "%") + "%"
        rows = self.conn.execute(
            """SELECT id, relative_path, filename, extension,
                      file_size, modified_time, '', is_valid, 0 as rank
               FROM files
               WHERE filename LIKE ? AND is_valid=1
               LIMIT ?""",
            (pattern, limit)
        ).fetchall()
        return rows

    # ---- 统计操作 ----

    def get_statistics(self):
        """获取索引统计信息"""
        stats = {}
        row = self.conn.execute(
            "SELECT COUNT(*), SUM(file_size) FROM files WHERE is_valid=1"
        ).fetchone()
        stats["total_files"] = row[0] or 0
        stats["total_size"] = row[1] or 0

        rows = self.conn.execute(
            "SELECT extension, COUNT(*) FROM files WHERE is_valid=1 GROUP BY extension ORDER BY COUNT(*) DESC"
        ).fetchall()
        stats["by_extension"] = {row[0]: row[1] for row in rows}

        stats["root_path"] = self.get_root_path()
        stats["last_index_time"] = self.get_last_index_time()
        stats["file_types"] = self.get_file_types()

        if self.db_path and os.path.exists(self.db_path):
            stats["index_size"] = os.path.getsize(self.db_path)
        else:
            stats["index_size"] = 0

        return stats

    def get_file_content(self, file_id):
        """获取文件内容（从FTS表查询，用于离线查看）"""
        row = self.conn.execute(
            "SELECT content FROM files_fts WHERE rowid=?", (file_id,)
        ).fetchone()
        return row[0] if row else ""

    def get_file_by_id(self, file_id):
        """根据ID获取文件完整信息（不含content，内容从FTS获取）"""
        row = self.conn.execute(
            """SELECT id, relative_path, filename, extension,
                      file_size, modified_time, is_valid
               FROM files WHERE id=?""",
            (file_id,)
        ).fetchone()
        return row

    def batch_insert_files(self, file_records):
        """批量插入文件记录
        file_records: list of (relative_path, filename, ext, size, mtime, index_time)
        """
        self.conn.executemany(
            """INSERT INTO files
               (relative_path, filename, extension, file_size, modified_time, index_time)
               VALUES (?, ?, ?, ?, ?, ?)""",
            file_records
        )
        self.conn.commit()

    def batch_insert_fts(self, fts_records):
        """批量插入FTS记录
        fts_records: list of (rowid, filename_tokens, content_tokens)
        """
        self.conn.executemany(
            "INSERT INTO files_fts (rowid, filename, content) VALUES (?, ?, ?)",
            fts_records
        )
        self.conn.commit()

    def get_all_files(self, limit=10000):
        """获取所有有效文件（用于空搜索时显示）"""
        rows = self.conn.execute(
            """SELECT id, relative_path, filename, extension,
                      file_size, modified_time, '', is_valid, 0 as rank
               FROM files
               WHERE is_valid=1
               ORDER BY modified_time DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()
        return rows
