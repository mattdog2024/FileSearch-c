"""数据库操作模块 - SQLite + FTS5 全文索引（性能优化版）
- FTS5 contentless 模式，减少数据库体积
- 独立 file_contents 表存储文件内容（用于离线预览）
- 批量操作 + 单事务写入
"""
import sqlite3
import os
import json
import time
from contextlib import contextmanager


class IndexDatabase:
    """索引数据库管理"""

    # 数据库版本号，用于迁移检测
    DB_VERSION = "2"

    def __init__(self, db_path=None):
        self.db_path = db_path
        self.conn = None

    def create(self, db_path):
        """创建新索引数据库"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self._create_tables()
        self.set_meta("db_version", self.DB_VERSION)
        return self

    def open(self, db_path):
        """打开已有索引数据库"""
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"索引文件不存在: {db_path}")
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=-64000")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        return self

    def toggle_synchronous(self, fast_mode=True):
        """切换 PRAGMA synchronous 模式
        fast_mode=True: synchronous=OFF (索引期间，写入速度提升 2-3 倍)
        fast_mode=False: synchronous=NORMAL (正常使用，数据安全)
        """
        if fast_mode:
            self.conn.execute("PRAGMA synchronous=OFF")
        else:
            self.conn.execute("PRAGMA synchronous=NORMAL")

    def optimize_fts(self):
        """FTS5 索引优化：合并碎片化的 B-Tree 块
        索引大量数据后运行，可提升搜索性能
        """
        try:
            self.conn.execute("INSERT INTO files_fts(files_fts) VALUES('optimize')")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass

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
        """创建数据表"""
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

            CREATE TABLE IF NOT EXISTS file_contents (
                file_id INTEGER PRIMARY KEY,
                content TEXT
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
        """创建FTS5全文搜索表（contentless模式，体积更小）
        content='' 表示不存储原文，只建倒排索引
        原文存在 file_contents 表中
        """
        self.conn.executescript("""
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                filename,
                content,
                content='',
                tokenize='unicode61'
            );
        """)
        self.conn.commit()

    def needs_migration(self):
        """检查是否需要从旧版迁移"""
        version = self.get_meta("db_version", "1")
        return version != self.DB_VERSION

    def migrate(self):
        """从旧版数据库迁移到新版"""
        old_version = self.get_meta("db_version", "1")
        if old_version == self.DB_VERSION:
            return

        # v1 -> v2: 添加 file_contents 表，迁移 FTS 内容
        if old_version == "1":
            try:
                self.conn.executescript("""
                    CREATE TABLE IF NOT EXISTS file_contents (
                        file_id INTEGER PRIMARY KEY,
                        content TEXT
                    );
                """)
                # 检查旧 FTS 表是否有内容列
                cursor = self.conn.execute("PRAGMA table_info(files_fts)")
                cols = [row[1] for row in cursor.fetchall()]
                if "content" in cols:
                    # 从旧 FTS 表迁移内容到 file_contents
                    try:
                        self.conn.execute("""
                            INSERT OR REPLACE INTO file_contents (file_id, content)
                            SELECT f.id, fts.content
                            FROM files f
                            JOIN files_fts fts ON fts.rowid = f.id
                            WHERE fts.content IS NOT NULL AND fts.content != ''
                        """)
                        self.conn.commit()
                    except Exception:
                        pass

                    # 重建 FTS 表为 contentless 模式
                    self.conn.executescript("""
                        DROP TABLE IF EXISTS files_fts;
                        CREATE VIRTUAL TABLE files_fts USING fts5(
                            filename, content,
                            content='',
                            tokenize='unicode61'
                        );
                    """)
                    # 重新填充 FTS 索引
                    self.conn.execute("""
                        INSERT INTO files_fts (rowid, filename, content)
                        SELECT f.id, f.filename, COALESCE(fc.content, '')
                        FROM files f
                        LEFT JOIN file_contents fc ON fc.file_id = f.id
                        WHERE f.is_valid = 1
                    """)
                    self.conn.commit()
                self.set_meta("db_version", self.DB_VERSION)
            except Exception:
                pass

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

    def get_all_indexed_files_dict(self):
        """获取所有已索引的有效文件信息（用于增量索引比对）
        返回: {relative_path: (id, file_size, modified_time)}
        """
        rows = self.conn.execute(
            "SELECT relative_path, id, file_size, modified_time FROM files WHERE is_valid=1"
        ).fetchall()
        return {row[0]: (row[1], row[2], row[3]) for row in rows}

    def insert_file(self, relative_path, filename, extension, file_size,
                    modified_time, index_time=None):
        """插入文件记录"""
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
        """更新文件记录"""
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
        """获取所有已索引的有效文件路径（兼容旧接口）"""
        rows = self.conn.execute(
            "SELECT relative_path, file_size, modified_time FROM files WHERE is_valid=1"
        ).fetchall()
        return {row[0]: (row[1], row[2]) for row in rows}

    # ---- FTS操作 ----

    def insert_fts(self, rowid, filename_tokens, content_tokens):
        """插入FTS记录"""
        self.conn.execute(
            "INSERT INTO files_fts (rowid, filename, content) VALUES (?, ?, ?)",
            (rowid, filename_tokens, content_tokens)
        )

    def delete_fts(self, rowid):
        """删除FTS记录（contentless模式需要提供原始内容）"""
        try:
            # 从 file_contents 获取原始内容
            row = self.conn.execute(
                "SELECT content FROM file_contents WHERE file_id=?", (rowid,)
            ).fetchone()
            content = row[0] if row else ""

            # 获取文件名
            frow = self.conn.execute(
                "SELECT filename FROM files WHERE id=?", (rowid,)
            ).fetchone()
            filename = frow[0] if frow else ""

            # contentless FTS5 删除需要提供与插入时相同的 token
            self.conn.execute(
                "DELETE FROM files_fts WHERE rowid=? AND filename=? AND content=?",
                (rowid, filename, content)
            )
        except sqlite3.OperationalError:
            pass

    def get_fts_data_for_delete(self, file_ids):
        """批量获取 FTS 删除所需的原始数据（单条查询替代 N*3 条查询）
        返回: [(rowid, filename, content), ...]
        """
        if not file_ids:
            return []
        placeholders = ",".join("?" * len(file_ids))
        rows = self.conn.execute(
            f"""SELECT f.id, f.filename, COALESCE(fc.content, '')
                FROM files f
                LEFT JOIN file_contents fc ON fc.file_id = f.id
                WHERE f.id IN ({placeholders})""",
            file_ids
        ).fetchall()
        return rows

    def insert_content(self, file_id, content):
        """存储文件内容（用于离线预览）"""
        self.conn.execute(
            "INSERT OR REPLACE INTO file_contents (file_id, content) VALUES (?, ?)",
            (file_id, content)
        )

    def update_content(self, file_id, content):
        """更新文件内容"""
        self.conn.execute(
            "INSERT OR REPLACE INTO file_contents (file_id, content) VALUES (?, ?)",
            (file_id, content)
        )

    # ---- 批量操作（高性能） ----

    def batch_insert_files(self, file_records):
        """批量插入文件记录
        file_records: list of (relative_path, filename, ext, size, mtime, index_time)
        返回: list of inserted file_ids
        """
        cursor = self.conn.executemany(
            """INSERT INTO files
               (relative_path, filename, extension, file_size, modified_time, index_time)
               VALUES (?, ?, ?, ?, ?, ?)""",
            file_records
        )
        return cursor.lastrowid

    def batch_insert_files_with_ids(self, file_records):
        """批量插入文件记录并返回ID列表
        性能优化：先获取当前最大ID，一次 executemany 插入，ID 自增连续
        避免了逐条 INSERT（速度提升 10-50 倍）
        """
        if not file_records:
            return []
        # 获取当前最大ID
        row = self.conn.execute("SELECT COALESCE(MAX(id), 0) FROM files").fetchone()
        start_id = row[0] + 1
        # 单次 executemany 插入（不获取 lastrowid）
        self.conn.executemany(
            """INSERT INTO files
               (relative_path, filename, extension, file_size, modified_time, index_time)
               VALUES (?, ?, ?, ?, ?, ?)""",
            file_records
        )
        # ID 是从 start_id 开始的连续整数（AUTOINCREMENT 保证）
        return list(range(start_id, start_id + len(file_records)))

    def batch_insert_fts(self, fts_records):
        """批量插入FTS记录
        fts_records: list of (rowid, filename_tokens, content_tokens)
        """
        self.conn.executemany(
            "INSERT INTO files_fts (rowid, filename, content) VALUES (?, ?, ?)",
            fts_records
        )

    def batch_insert_contents(self, content_records):
        """批量存储文件内容
        content_records: list of (file_id, content)
        """
        self.conn.executemany(
            "INSERT OR REPLACE INTO file_contents (file_id, content) VALUES (?, ?)",
            content_records
        )

    def batch_update_files(self, update_records):
        """批量更新文件记录
        update_records: list of (file_size, modified_time, index_time, file_id)
        """
        self.conn.executemany(
            """UPDATE files SET file_size=?, modified_time=?, index_time=?, is_valid=1
               WHERE id=?""",
            update_records
        )

    def batch_mark_invalid(self, file_ids):
        """批量标记文件为无效"""
        if not file_ids:
            return
        placeholders = ",".join("?" * len(file_ids))
        self.conn.execute(
            f"UPDATE files SET is_valid=0 WHERE id IN ({placeholders})",
            file_ids
        )

    # ---- 搜索操作 ----

    def search_fts(self, query, limit=500):
        """FTS5全文搜索"""
        try:
            rows = self.conn.execute(
                """SELECT f.id, f.relative_path, f.filename, f.extension,
                          f.file_size, f.modified_time,
                          COALESCE(fc.content, '') as content,
                          f.is_valid, rank
                   FROM files_fts fts
                   JOIN files f ON f.id = fts.rowid
                   LEFT JOIN file_contents fc ON fc.file_id = f.id
                   WHERE files_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (query, limit)
            ).fetchall()
            return rows
        except sqlite3.OperationalError as e:
            if "no such table" in str(e) or "fts5" in str(e).lower():
                return []
            raise

    def search_like(self, keyword, limit=500):
        """LIKE模糊搜索（用于通配符查询，搜文件名+内容）"""
        pattern = keyword.replace("*", "%").replace("?", "_")
        if not pattern.startswith("%"):
            pattern = "%" + pattern
        if not pattern.endswith("%"):
            pattern = pattern + "%"

        rows = self.conn.execute(
            """SELECT f.id, f.relative_path, f.filename, f.extension,
                      f.file_size, f.modified_time,
                      COALESCE(fc.content, '') as content,
                      f.is_valid, 0 as rank
               FROM files f
               LEFT JOIN file_contents fc ON fc.file_id = f.id
               WHERE (f.filename LIKE ? OR COALESCE(fc.content, '') LIKE ?)
                 AND f.is_valid=1
               LIMIT ?""",
            (pattern, pattern, limit)
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
        """获取文件内容（从 file_contents 表）"""
        row = self.conn.execute(
            "SELECT content FROM file_contents WHERE file_id=?", (file_id,)
        ).fetchone()
        return row[0] if row else ""

    def get_file_by_id(self, file_id):
        """根据ID获取文件完整信息"""
        row = self.conn.execute(
            """SELECT id, relative_path, filename, extension,
                      file_size, modified_time, is_valid
               FROM files WHERE id=?""",
            (file_id,)
        ).fetchone()
        return row

    def get_all_files(self, limit=10000):
        """获取所有有效文件（用于空搜索时显示）"""
        rows = self.conn.execute(
            """SELECT f.id, f.relative_path, f.filename, f.extension,
                      f.file_size, f.modified_time, '', f.is_valid, 0 as rank
               FROM files f
               WHERE f.is_valid=1
               ORDER BY f.modified_time DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()
        return rows
