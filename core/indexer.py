"""索引引擎 - 扫描文件、解析内容、构建索引（极速版）
优化：跳过 jieba 预分词，让 FTS5 unicode61 直接处理原文
"""
import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtCore import QObject, pyqtSignal, QThread

from .database import IndexDatabase
from .text_utils import clean_text, tokenize_filename
from .parsers import parse_file, get_supported_extensions

logger = logging.getLogger(__name__)

# 单个文件最大大小 (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

# 最大索引页数（PDF等）
MAX_PAGES = 200

# 并行解析线程数
MAX_WORKERS = 4


class IndexerWorker(QObject):
    """索引工作线程（在QThread中运行）"""

    # 信号
    progress = pyqtSignal(int, int, str)  # current, total, current_file
    phase_changed = pyqtSignal(str)  # 阶段名
    finished = pyqtSignal(int, int, int)  # total_files, new_files, updated_files
    error = pyqtSignal(str)
    log_message = pyqtSignal(str)

    def __init__(self, root_path, db_path, file_types=None, is_incremental=True):
        super().__init__()
        self.root_path = root_path
        self.db_path = db_path
        self.file_types = file_types or get_supported_extensions()
        self.is_incremental = is_incremental
        self._cancelled = False
        self._start_time = 0
        self._last_progress_time = 0

    def cancel(self):
        """取消索引"""
        self._cancelled = True

    def run(self):
        """执行索引（在工作线程中调用）"""
        try:
            self._do_index()
        except Exception as e:
            self.error.emit(f"索引出错: {e}")
            logger.exception("索引出错")

    def _format_eta(self, seconds):
        """格式化预计剩余时间"""
        if seconds < 60:
            return f"{int(seconds)}秒"
        elif seconds < 3600:
            return f"{int(seconds // 60)}分{int(seconds % 60)}秒"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}小时{minutes}分"

    def _do_index(self):
        """主索引流程"""
        self._start_time = time.time()
        db = IndexDatabase()

        # 创建或打开数据库
        is_new = not os.path.exists(self.db_path)
        if is_new:
            db.create(self.db_path)
            db.set_root_path(self.root_path)
            db.set_file_types(self.file_types)
            db.create_fts_table()
        else:
            db.open(self.db_path)

        # 确保FTS表存在
        try:
            db.create_fts_table()
        except Exception:
            pass

        # 阶段1: 扫描文件
        self.phase_changed.emit("scanning")
        self.log_message.emit(f"正在扫描目录: {self.root_path}")
        all_files = self._scan_files()

        if self._cancelled:
            db.close()
            return

        total = len(all_files)
        self.log_message.emit(f"找到 {total} 个文件")

        if total == 0:
            db.set_last_index_time()
            db.close()
            self.phase_changed.emit("done")
            self.finished.emit(0, 0, 0)
            return

        # 获取已索引的文件信息（用于增量索引）
        existing_files = {}
        if self.is_incremental and not is_new:
            existing_files = db.get_all_indexed_paths()

        # 阶段2: 解析文件内容（多线程 + 无jieba预分词）
        self.phase_changed.emit("parsing")
        new_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        # 批量处理
        batch_records = []
        batch_fts = []
        batch_size = 100  # 增大批量大小

        # 使用线程池并行解析
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # 提交所有任务
            future_to_file = {}
            for i, filepath in enumerate(all_files):
                if self._cancelled:
                    break

                rel_path = os.path.relpath(filepath, self.root_path)
                filename = os.path.basename(filepath)
                ext = os.path.splitext(filepath)[1].lower()

                try:
                    stat = os.stat(filepath)
                    file_size = stat.st_size
                    mtime = stat.st_mtime
                except OSError:
                    skipped_count += 1
                    continue

                # 检查是否需要跳过（增量索引）
                if rel_path in existing_files:
                    old_size, old_mtime = existing_files[rel_path]
                    if old_size == file_size and abs(old_mtime - mtime) < 1:
                        skipped_count += 1
                        del existing_files[rel_path]
                        self.progress.emit(i + 1, total, filename)
                        continue

                # 检查文件大小
                if file_size > MAX_FILE_SIZE:
                    self.log_message.emit(f"跳过大文件 ({file_size // 1024 // 1024}MB): {filename}")
                    skipped_count += 1
                    self.progress.emit(i + 1, total, filename)
                    continue

                # 提交解析任务
                future = executor.submit(self._parse_single_file, filepath, ext, filename)
                future_to_file[future] = (i, filepath, rel_path, filename, ext, file_size, mtime)

            # 处理完成的任务
            for future in as_completed(future_to_file):
                if self._cancelled:
                    break

                i, filepath, rel_path, filename, ext, file_size, mtime = future_to_file[future]

                try:
                    content = future.result()
                except Exception as e:
                    error_count += 1
                    logger.debug(f"解析失败 {filename}: {e}")
                    content = ""

                # 只分词文件名（很短，很快），内容直接存原文让FTS5处理
                filename_tokens = tokenize_filename(filename)

                now = time.time()

                # 检查是否已存在（更新）
                existing = db.get_file_by_path(rel_path)
                if existing:
                    file_id = existing[0]
                    db.update_file(file_id, file_size, mtime, now)
                    db.delete_fts(file_id)
                    db.insert_fts(file_id, filename_tokens, content)  # 直接存原文
                    updated_count += 1
                    if rel_path in existing_files:
                        del existing_files[rel_path]
                else:
                    batch_records.append((rel_path, filename, ext, file_size, mtime, now))
                    batch_fts.append((None, filename_tokens, content))  # rowid稍后填充
                    new_count += 1

                    # 批量写入
                    if len(batch_records) >= batch_size:
                        self._flush_batch(db, batch_records, batch_fts)
                        batch_records = []
                        batch_fts = []

                # 节流进度更新（最多每200ms一次）
                now_time = time.time()
                if now_time - self._last_progress_time > 0.2:
                    self.progress.emit(i + 1, total, filename)
                    self._last_progress_time = now_time

                # 每200个文件显示一次详细进度
                if (i + 1) % 200 == 0:
                    elapsed = time.time() - self._start_time
                    processed = new_count + updated_count + skipped_count
                    if processed > 0:
                        avg_time = elapsed / processed
                        remaining = (total - processed) * avg_time
                        eta_str = self._format_eta(remaining)
                        self.log_message.emit(
                            f"进度: {i + 1}/{total} | 新增: {new_count} | 更新: {updated_count} | "
                            f"跳过: {skipped_count} | 预计剩余: {eta_str}"
                        )

        # 刷新剩余批次
        if batch_records:
            self._flush_batch(db, batch_records, batch_fts)

        # 标记不再存在的文件为无效
        if self.is_incremental and existing_files:
            for rel_path in existing_files:
                existing = db.get_file_by_path(rel_path)
                if existing:
                    db.mark_invalid(existing[0])

        # 更新元数据
        db.set_last_index_time()

        if not self.is_incremental:
            db.mark_all_invalid()

        db.close()

        elapsed = time.time() - self._start_time
        self.log_message.emit(
            f"索引完成! 总计: {total} | 新增: {new_count} | 更新: {updated_count} | "
            f"跳过: {skipped_count} | 错误: {error_count} | 耗时: {self._format_eta(elapsed)}"
        )
        self.phase_changed.emit("done")
        self.finished.emit(total, new_count, updated_count)

    def _parse_single_file(self, filepath, ext, filename):
        """解析单个文件（可并行执行）"""
        try:
            content = parse_file(filepath, ext)
            return clean_text(content)
        except Exception as e:
            logger.debug(f"解析失败 {filename}: {e}")
            return ""

    def _flush_batch(self, db, batch_records, batch_fts):
        """批量写入数据库"""
        try:
            for idx, rec in enumerate(batch_records):
                rel_path, filename, ext, file_size, mtime, now = rec
                file_id = db.insert_file(rel_path, filename, ext, file_size, mtime, now)
                # 更新FTS记录的rowid
                batch_fts[idx] = (file_id, batch_fts[idx][1], batch_fts[idx][2])

            # 批量插入FTS
            db.batch_insert_fts(batch_fts)
        except Exception as e:
            logger.error(f"批量写入失败: {e}")
            db.conn.rollback()

    def _scan_files(self):
        """扫描目录，返回所有匹配的文件路径"""
        files = []
        ext_set = set(e.lower() for e in self.file_types)

        for dirpath, dirnames, filenames in os.walk(self.root_path):
            if self._cancelled:
                break

            # 跳过隐藏目录和系统目录
            dirnames[:] = [
                d for d in dirnames
                if not d.startswith(".") and d not in ("$RECYCLE.BIN", "System Volume Information", "node_modules")
            ]

            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in ext_set:
                    filepath = os.path.join(dirpath, filename)
                    files.append(filepath)

        return files


class IndexerThread(QThread):
    """索引线程包装器"""

    def __init__(self, root_path, db_path, file_types=None, is_incremental=True, parent=None):
        super().__init__(parent)
        self.worker = IndexerWorker(root_path, db_path, file_types, is_incremental)
        self.worker.moveToThread(self)

        # 转发信号
        self.worker.progress.connect(lambda c, t, f: self.progress.emit(c, t, f))
        self.worker.phase_changed.connect(lambda p: self.phase_changed.emit(p))
        self.worker.finished.connect(lambda t, n, u: self.finished.emit(t, n, u))
        self.worker.error.connect(lambda e: self.error.emit(e))
        self.worker.log_message.connect(lambda m: self.log_message.emit(m))

    # 信号
    progress = pyqtSignal(int, int, str)
    phase_changed = pyqtSignal(str)
    finished = pyqtSignal(int, int, int)
    error = pyqtSignal(str)
    log_message = pyqtSignal(str)

    def run(self):
        self.worker.run()

    def cancel(self):
        self.worker.cancel()
