"""索引引擎 - 扫描文件、解析内容、构建索引（v2.5.0 真多核版）
优化：
- os.scandir + stat 缓存（避免重复系统调用）
- ProcessPoolExecutor 真多核并行（绕过 GIL，解析+分词不再被线程锁串行化）
- worker 进程预加载 jieba 词典（initializer 并行加载 + 词典缺失 fail-fast）
- wait(FIRST_COMPLETED) + inflight_cap 有界提交（避免大语料 pickled 结果堆积内存）
- 自适应进程数
- 单事务批量写入
- contentless FTS5 + 独立内容存储
- 索引期间 PRAGMA synchronous=OFF（写入速度提升 2-3x）
- 批量 executemany（避免逐条 INSERT）
- 更新文件采用"标记旧记录无效 + 插入新记录"策略（避免 contentless FTS5 DELETE 重分词开销）
- 分词前内容截断（存储范围 == 搜索范围 == snippet 范围，无 gap）
- 索引结束 FTS5 optimize 合并碎片
"""
import os
import time
import logging
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from concurrent.futures.process import BrokenProcessPool
from PyQt5.QtCore import QObject, pyqtSignal, QThread

from .database import IndexDatabase
from .index_worker import parse_and_tokenize, _init_worker
from .parsers import get_supported_extensions

logger = logging.getLogger(__name__)

# 单个文件最大大小 (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

# 自适应进程数
def _get_optimal_workers():
    """根据 CPU 核心数确定最佳进程数"""
    try:
        cpu_count = os.cpu_count() or 2
    except Exception:
        cpu_count = 2
    return min(max(cpu_count, 4), 8)

MAX_WORKERS = _get_optimal_workers()


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
            # 检查是否需要迁移
            if db.needs_migration():
                self.log_message.emit("正在升级数据库结构...")
                db.migrate()
                self.log_message.emit("数据库升级完成")

        # 确保FTS表存在
        try:
            db.create_fts_table()
        except Exception:
            pass

        # ---- 性能优化：索引期间关闭 fsync 同步，写入速度提升 2-3 倍 ----
        db.toggle_synchronous(fast_mode=True)

        # 阶段1: 扫描文件（使用 os.scandir + stat 缓存）
        self.phase_changed.emit("scanning")
        self.log_message.emit(f"正在扫描目录: {self.root_path}")
        # file_infos: {filepath: (rel_path, filename, ext, file_size, mtime)}
        file_infos = self._scan_files()

        if self._cancelled:
            db.toggle_synchronous(fast_mode=False)
            db.close()
            return

        total = len(file_infos)
        self.log_message.emit(f"找到 {total} 个文件")

        if total == 0:
            db.set_last_index_time()
            db.toggle_synchronous(fast_mode=False)
            db.close()
            self.phase_changed.emit("done")
            self.finished.emit(0, 0, 0)
            return

        # 获取已索引的文件信息（用于增量索引）
        existing_files = {}
        if self.is_incremental and not is_new:
            existing_files = db.get_all_indexed_files_dict()

        # 阶段2: 解析文件内容 + 分词（在进程池 worker 中完成，绕过 GIL 真多核）
        self.phase_changed.emit("parsing")
        new_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        processed_count = 0  # 进程崩溃日志用到，预先定义避免 NameError

        # 批量写入缓冲（合并 new + update 的插入操作）
        batch_new = []           # [(rel_path, filename, ext, size, mtime, index_time)]
        batch_content = []       # [(None, content)] 占位
        batch_fts = []           # [(None, filename_tokens, content_tokens)]
        batch_mark_invalid = []  # [file_id, ...] 需要标记为无效的旧记录
        # 增大批量：单事务更多数据，减少事务开销
        batch_size = 500

        # 使用进程池并行解析 + 分词（绕过 GIL，真多核）
        # 去掉 total//10 退化：进程模式下小文件集也该并行
        workers = min(MAX_WORKERS, max(1, total))
        # 有界提交：限制在途 future 数，避免大语料 GB 级 pickled 结果堆积内存
        # （每个 worker 结果最多 ~2M 内容 + tokens，cap=workers*2 → 峰值 ~32-48MB）
        inflight_cap = max(workers * 2, 4)

        broken = False  # BrokenProcessPool 标志：触发后跳过 optimize_fts
        pool = None
        future_to_file = {}
        try:
            try:
                pool = ProcessPoolExecutor(
                    max_workers=workers,
                    initializer=_init_worker,
                )

                file_iter = iter(file_infos.items())
                exhausted = False

                def refill():
                    """按需补充提交，维持在途 future 数 <= inflight_cap。"""
                    nonlocal exhausted, skipped_count
                    while (
                        not exhausted
                        and not self._cancelled
                        and len(future_to_file) < inflight_cap
                    ):
                        try:
                            filepath, info = next(file_iter)
                        except StopIteration:
                            exhausted = True
                            return
                        rel_path, filename, ext, file_size, mtime = info

                        # 增量索引：mtime+size 未变则跳过
                        if rel_path in existing_files:
                            old_id, old_size, old_mtime = existing_files[rel_path]
                            if old_size == file_size and abs(old_mtime - mtime) < 1:
                                skipped_count += 1
                                del existing_files[rel_path]
                                continue

                        # 检查文件大小
                        if file_size > MAX_FILE_SIZE:
                            self.log_message.emit(
                                f"跳过大文件 ({file_size // 1024 // 1024}MB): {filename}"
                            )
                            skipped_count += 1
                            continue

                        future = pool.submit(parse_and_tokenize, filepath, ext, filename)
                        future_to_file[future] = (rel_path, filename, ext, file_size, mtime)

                refill()

                # wait(FIRST_COMPLETED) + 短 timeout：既能在有结果时立即处理，
                # 又能定期回到 while 条件检查 self._cancelled，保证取消响应性
                while future_to_file and not self._cancelled:
                    done, _ = wait(
                        fs=list(future_to_file.keys()),
                        timeout=0.2,
                        return_when=FIRST_COMPLETED,
                    )
                    if not done:
                        continue  # timeout：回到 while 重新检查 _cancelled
                    for future in done:
                        meta = future_to_file.pop(future)
                        rel_path, filename, ext, file_size, mtime = meta
                        processed_count += 1

                        try:
                            # worker 返回 (stored_content, filename_tokens, content_tokens)
                            content, filename_tokens, content_tokens = future.result()
                        except BrokenProcessPool as e:
                            # 子进程原生库（pdfplumber/PyPDF2/python-docx）segfault
                            # → 进程池标记为 broken，后续 submit/result 全部抛此异常
                            self.error.emit(
                                f"索引进程崩溃（可能损坏的文件触发原生库崩溃）: {e}"
                            )
                            logger.error("BrokenProcessPool during indexing", exc_info=True)
                            broken = True
                            break
                        except Exception as e:
                            error_count += 1
                            logger.debug(f"解析失败 {filename}: {e}")
                            content, filename_tokens, content_tokens = "", "", ""

                        now = time.time()

                        # 检查是否已存在（更新）：采用 "标记旧记录无效 + 插入新记录" 策略
                        # 避免 contentless FTS5 删除时需要重新分词的昂贵开销
                        if rel_path in existing_files:
                            old_id, old_size, old_mtime = existing_files[rel_path]
                            batch_mark_invalid.append(old_id)
                            del existing_files[rel_path]
                            updated_count += 1
                        else:
                            new_count += 1  # 仅统计意义上的"新文件"

                        # 统一作为"新记录"插入（外加标记旧记录无效）
                        batch_new.append((rel_path, filename, ext, file_size, mtime, now))
                        batch_content.append((None, content))
                        batch_fts.append((None, filename_tokens, content_tokens))

                        if len(batch_new) >= batch_size:
                            self._flush_batch(db, batch_new, batch_content, batch_fts, batch_mark_invalid)
                            batch_new = []
                            batch_content = []
                            batch_fts = []
                            batch_mark_invalid = []

                        # 节流进度更新
                        if now - self._last_progress_time > 0.2:
                            self.progress.emit(processed_count + skipped_count, total, filename)
                            self._last_progress_time = now

                        # 每200个文件显示一次详细进度
                        if processed_count % 200 == 0:
                            elapsed = time.time() - self._start_time
                            processed = new_count + updated_count + skipped_count
                            if processed > 0:
                                avg_time = elapsed / processed
                                remaining = (total - processed) * avg_time
                                eta_str = self._format_eta(remaining)
                                self.log_message.emit(
                                    f"进度: {processed_count + skipped_count}/{total} | "
                                    f"新增: {new_count} | 更新: {updated_count} | "
                                    f"跳过: {skipped_count} | 预计剩余: {eta_str}"
                                )

                    if broken:
                        break
                    # 补充提交，维持 inflight 水位
                    refill()

                # 刷新剩余批次
                if batch_new:
                    self._flush_batch(db, batch_new, batch_content, batch_fts, batch_mark_invalid)

                # 标记不再存在的文件为无效（已删除的文件）
                if self.is_incremental and existing_files:
                    invalid_ids = [v[0] for v in existing_files.values()]
                    if invalid_ids:
                        db.batch_mark_invalid(invalid_ids)

                # ---- FTS5 索引优化：合并 B-Tree 碎片，提升搜索性能 ----
                # 取消 / 进程崩溃时跳过（optimize 对不完整索引意义不大，且耗时）
                if not self._cancelled and not broken:
                    self.log_message.emit("正在优化 FTS 索引...")
                    db.optimize_fts()

                # 更新元数据
                db.set_last_index_time()
            except BrokenProcessPool as e:
                # 进程池在 submit/refill 阶段就 broken（如 initializer 中 jieba 词典缺失）
                self.error.emit(
                    f"索引进程崩溃（可能 jieba 词典缺失或原生库崩溃）: {e}"
                )
                logger.error("BrokenProcessPool during indexing", exc_info=True)
                broken = True
        finally:
            # 取消 pending future（对已 running 的无效）；清理在途映射
            for f in list(future_to_file.keys()):
                f.cancel()
            future_to_file.clear()
            if pool is not None:
                try:
                    pool.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    # Python < 3.9 无 cancel_futures 参数
                    pool.shutdown(wait=False)
            # 确保 DB 总是恢复安全模式并关闭（即使取消/崩溃/异常，避免残留 fast-mode）
            try:
                db.toggle_synchronous(fast_mode=False)
            except Exception:
                pass
            try:
                db.close()
            except Exception:
                pass

        elapsed = time.time() - self._start_time
        if broken:
            # 进程崩溃：error 已 emit，这里只记日志，不 emit finished（避免误导用户"完成"）
            self.log_message.emit(
                f"索引因进程崩溃中止 | 已处理: {processed_count} | 耗时: {self._format_eta(elapsed)}"
            )
        elif self._cancelled:
            self.log_message.emit(
                f"索引已取消 | 新增: {new_count} | 更新: {updated_count} | "
                f"跳过: {skipped_count} | 耗时: {self._format_eta(elapsed)}"
            )
            self.phase_changed.emit("done")
            self.finished.emit(total, new_count, updated_count)
        else:
            self.log_message.emit(
                f"索引完成! 总计: {total} | 新增: {new_count} | 更新: {updated_count} | "
                f"跳过: {skipped_count} | 错误: {error_count} | 耗时: {self._format_eta(elapsed)}"
            )
            self.phase_changed.emit("done")
            self.finished.emit(total, new_count, updated_count)

    def _flush_batch(self, db, batch_new, batch_content, batch_fts, batch_mark_invalid=None):
        """批量写入文件记录（单事务）

        batch_new: [(rel_path, filename, ext, size, mtime, index_time), ...]
        batch_content: [(None, content), ...] 占位
        batch_fts: [(None, filename_tokens, content_tokens), ...]
        batch_mark_invalid: [file_id, ...] 需要标记为无效的旧记录（更新场景）

        性能优化：
        - 批量 executemany 插入（10-50x 比逐条 INSERT 快）
        - 单事务包裹所有操作
        - 旧记录标记为无效，避免 contentless FTS5 昂贵的 DELETE 重分词
        """
        try:
            with db.transaction():
                # 1. 标记需要更新的旧记录为无效
                if batch_mark_invalid:
                    db.batch_mark_invalid(batch_mark_invalid)

                # 2. 批量插入新文件记录（executemany 一次性写入）
                ids = db.batch_insert_files_with_ids(batch_new)

                # 3. 分离 content 和 fts 记录
                content_records = []
                fts_records = []
                for idx, file_id in enumerate(ids):
                    # content
                    if idx < len(batch_content):
                        content = batch_content[idx][1]
                        if content:
                            content_records.append((file_id, content))
                    # fts
                    if idx < len(batch_fts):
                        fts_records.append((file_id, batch_fts[idx][1], batch_fts[idx][2]))

                # 4. 批量插入内容和 FTS（executemany）
                if content_records:
                    db.batch_insert_contents(content_records)
                if fts_records:
                    db.batch_insert_fts(fts_records)

            return ids
        except Exception as e:
            logger.error(f"批量写入失败: {e}")
            try:
                db.conn.rollback()
            except Exception:
                pass
            return []

    def _scan_files(self):
        """扫描目录，返回文件信息字典
        使用 os.scandir + 缓存 stat 结果（避免重复系统调用）
        返回: {filepath: (rel_path, filename, ext, file_size, mtime)}
        """
        file_infos = {}
        ext_set = set(e.lower() for e in self.file_types)
        skip_dirs = {"$RECYCLE.BIN", "System Volume Information", "node_modules", ".git"}
        root = self.root_path

        def _scan_recursive(directory):
            """递归扫描（使用 os.scandir + stat 缓存）"""
            if self._cancelled:
                return
            try:
                with os.scandir(directory) as it:
                    for entry in it:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                dirname = entry.name
                                if dirname not in skip_dirs and not dirname.startswith("."):
                                    _scan_recursive(entry.path)
                            elif entry.is_file(follow_symlinks=False):
                                filename = entry.name
                                ext = os.path.splitext(filename)[1].lower()
                                if ext in ext_set:
                                    # 缓存 stat 结果（DirEntry 已缓存，直接用）
                                    try:
                                        stat = entry.stat()
                                        file_size = stat.st_size
                                        mtime = stat.st_mtime
                                    except OSError:
                                        continue
                                    filepath = entry.path
                                    rel_path = os.path.relpath(filepath, root)
                                    file_infos[filepath] = (
                                        rel_path, filename, ext, file_size, mtime
                                    )
                        except OSError:
                            continue
            except PermissionError:
                pass
            except OSError:
                pass

        _scan_recursive(root)
        return file_infos


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
