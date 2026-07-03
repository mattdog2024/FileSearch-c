"""索引管理对话框 - 创建/更新索引、管理索引文件
现代化深色主题设计 - 精致版
"""
import os
import sys
import time
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QCheckBox, QProgressBar, QTextEdit,
    QComboBox, QMessageBox, QListWidget, QListWidgetItem, QRadioButton,
    QWidget, QFrame, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor

from core.indexer import IndexerThread
from core.parsers import get_supported_extensions


class IndexDialog(QDialog):
    """索引管理对话框"""

    def __init__(self, search_engine, parent=None):
        super().__init__(parent)
        self.search_engine = search_engine
        self.indexer_thread = None
        self._setup_ui()
        self._refresh_index_list()

    def _setup_ui(self):
        self.setWindowTitle("索引管理")
        self.setMinimumSize(720, 680)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ---- 已加载的索引列表 ----
        loaded_header = QLabel("已加载的索引")
        loaded_header.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 14px;
                font-weight: 600;
                padding: 4px 0;
            }
        """)
        layout.addWidget(loaded_header)

        loaded_card = QWidget()
        loaded_card.setStyleSheet("""
            QWidget {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 12px;
            }
        """)
        # 添加阴影
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        loaded_card.setGraphicsEffect(shadow)

        loaded_layout = QVBoxLayout(loaded_card)
        loaded_layout.setContentsMargins(16, 16, 16, 16)
        loaded_layout.setSpacing(12)

        self.index_list = QListWidget()
        self.index_list.setMaximumHeight(120)
        self.index_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
                color: #cdd6f4;
                font-size: 12px;
                padding: 8px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #313244;
            }
            QListWidget::item:selected {
                background-color: #313244;
                border-radius: 6px;
            }
        """)
        loaded_layout.addWidget(self.index_list)

        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("加载索引")
        self.btn_load.setObjectName("primaryBtn")
        self.btn_load.setMinimumHeight(36)
        self.btn_load.setCursor(Qt.PointingHandCursor)
        self.btn_load.clicked.connect(self._load_index)

        self.btn_unload = QPushButton("卸载选中")
        self.btn_unload.setObjectName("dangerBtn")
        self.btn_unload.setMinimumHeight(36)
        self.btn_unload.setCursor(Qt.PointingHandCursor)
        self.btn_unload.clicked.connect(self._unload_index)

        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_unload)
        btn_layout.addStretch()
        loaded_layout.addLayout(btn_layout)

        layout.addWidget(loaded_card)

        # ---- 创建/更新索引 ----
        create_header = QLabel("创建/更新索引")
        create_header.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 14px;
                font-weight: 600;
                padding: 4px 0;
            }
        """)
        layout.addWidget(create_header)

        create_card = QWidget()
        create_card.setStyleSheet("""
            QWidget {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 12px;
            }
        """)
        shadow2 = QGraphicsDropShadowEffect()
        shadow2.setBlurRadius(20)
        shadow2.setColor(QColor(0, 0, 0, 80))
        shadow2.setOffset(0, 4)
        create_card.setGraphicsEffect(shadow2)

        create_layout = QVBoxLayout(create_card)
        create_layout.setContentsMargins(16, 16, 16, 16)
        create_layout.setSpacing(14)

        # 源目录
        dir_row = QHBoxLayout()
        dir_label = QLabel("扫描目录:")
        dir_label.setStyleSheet("""
            QLabel {
                color: #a6adc8;
                font-size: 13px;
                font-weight: 500;
                min-width: 80px;
            }
        """)
        dir_row.addWidget(dir_label)

        self.txt_source = QComboBox()
        self.txt_source.setEditable(True)
        self.txt_source.setMinimumHeight(36)
        self.txt_source.setMinimumWidth(300)
        self.txt_source.setStyleSheet("""
            QComboBox {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
                color: #cdd6f4;
                padding: 6px 12px;
                font-size: 12px;
            }
            QComboBox:hover {
                border-color: #585b70;
            }
            QComboBox:focus {
                border-color: #89b4fa;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                color: #cdd6f4;
                selection-background-color: #313244;
            }
        """)
        # 添加常见盘符
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                self.txt_source.addItem(drive)
        dir_row.addWidget(self.txt_source, stretch=1)

        self.btn_browse_source = QPushButton("浏览...")
        self.btn_browse_source.setMinimumHeight(36)
        self.btn_browse_source.setMinimumWidth(80)
        self.btn_browse_source.setCursor(Qt.PointingHandCursor)
        self.btn_browse_source.clicked.connect(self._browse_source)
        dir_row.addWidget(self.btn_browse_source)
        create_layout.addLayout(dir_row)

        # 索引保存位置
        save_row = QHBoxLayout()
        save_label = QLabel("索引保存:")
        save_label.setStyleSheet("""
            QLabel {
                color: #a6adc8;
                font-size: 13px;
                font-weight: 500;
                min-width: 80px;
            }
        """)
        save_row.addWidget(save_label)

        self.txt_save = QComboBox()
        self.txt_save.setEditable(True)
        self.txt_save.setMinimumHeight(36)
        self.txt_save.setMinimumWidth(300)
        self.txt_save.setStyleSheet("""
            QComboBox {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
                color: #cdd6f4;
                padding: 6px 12px;
                font-size: 12px;
            }
            QComboBox:hover {
                border-color: #585b70;
            }
            QComboBox:focus {
                border-color: #89b4fa;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                color: #cdd6f4;
                selection-background-color: #313244;
            }
        """)
        # 默认保存到程序目录
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.txt_save.addItem(os.path.join(app_dir, "indexes"))
        save_row.addWidget(self.txt_save, stretch=1)

        self.btn_browse_save = QPushButton("浏览...")
        self.btn_browse_save.setMinimumHeight(36)
        self.btn_browse_save.setMinimumWidth(80)
        self.btn_browse_save.setCursor(Qt.PointingHandCursor)
        self.btn_browse_save.clicked.connect(self._browse_save)
        save_row.addWidget(self.btn_browse_save)
        create_layout.addLayout(save_row)

        # 文件类型选择
        type_label = QLabel("索引文件类型:")
        type_label.setStyleSheet("""
            QLabel {
                color: #a6adc8;
                font-size: 13px;
                font-weight: 500;
                padding: 4px 0;
            }
        """)
        create_layout.addWidget(type_label)

        type_container = QWidget()
        type_container.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        type_row = QHBoxLayout(type_container)
        type_row.setContentsMargins(12, 8, 12, 8)
        type_row.setSpacing(16)

        self.type_checks = {}
        for ext in get_supported_extensions():
            cb = QCheckBox(ext.upper().replace(".", ""))
            cb.setChecked(True)
            cb.setStyleSheet("""
                QCheckBox {
                    color: #cdd6f4;
                    font-size: 12px;
                    spacing: 6px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 4px;
                    border: 2px solid #585b70;
                    background-color: #1e1e2e;
                }
                QCheckBox::indicator:checked {
                    background-color: #89b4fa;
                    border-color: #89b4fa;
                }
                QCheckBox::indicator:hover {
                    border-color: #89b4fa;
                }
            """)
            self.type_checks[ext] = cb
            type_row.addWidget(cb)
        type_row.addStretch()
        create_layout.addWidget(type_container)

        # 索引模式
        mode_container = QWidget()
        mode_container.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        mode_row = QHBoxLayout(mode_container)
        mode_row.setContentsMargins(12, 8, 12, 8)
        mode_row.setSpacing(20)

        self.radio_incremental = QRadioButton("增量索引（推荐，只处理新增/修改的文件）")
        self.radio_incremental.setChecked(True)
        self.radio_incremental.setStyleSheet("""
            QRadioButton {
                color: #cdd6f4;
                font-size: 12px;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #585b70;
                background-color: #1e1e2e;
            }
            QRadioButton::indicator:checked {
                background-color: #89b4fa;
                border-color: #89b4fa;
            }
            QRadioButton::indicator:hover {
                border-color: #89b4fa;
            }
        """)

        self.radio_full = QRadioButton("全量重建（删除旧索引重新扫描）")
        self.radio_full.setStyleSheet("""
            QRadioButton {
                color: #cdd6f4;
                font-size: 12px;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #585b70;
                background-color: #1e1e2e;
            }
            QRadioButton::indicator:checked {
                background-color: #89b4fa;
                border-color: #89b4fa;
            }
            QRadioButton::indicator:hover {
                border-color: #89b4fa;
            }
        """)

        mode_row.addWidget(self.radio_incremental)
        mode_row.addWidget(self.radio_full)
        create_layout.addWidget(mode_container)

        # 开始/取消按钮
        action_row = QHBoxLayout()
        self.btn_start = QPushButton("开始索引")
        self.btn_start.setObjectName("successBtn")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self._start_index)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setMinimumHeight(40)
        self.btn_cancel.setMinimumWidth(100)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_index)

        action_row.addWidget(self.btn_start)
        action_row.addWidget(self.btn_cancel)
        action_row.addStretch()
        create_layout.addLayout(action_row)

        layout.addWidget(create_card)

        # ---- 进度区 ----
        progress_header = QLabel("进度")
        progress_header.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 14px;
                font-weight: 600;
                padding: 4px 0;
            }
        """)
        layout.addWidget(progress_header)

        progress_card = QWidget()
        progress_card.setStyleSheet("""
            QWidget {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 12px;
            }
        """)
        shadow3 = QGraphicsDropShadowEffect()
        shadow3.setBlurRadius(20)
        shadow3.setColor(QColor(0, 0, 0, 80))
        shadow3.setOffset(0, 4)
        progress_card.setGraphicsEffect(shadow3)

        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(16, 16, 16, 16)
        progress_layout.setSpacing(10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(24)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 12px;
                text-align: center;
                color: #cdd6f4;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #89b4fa, stop:1 #b4befe);
                border-radius: 11px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        self.lbl_progress = QLabel("就绪")
        self.lbl_progress.setStyleSheet("""
            QLabel {
                color: #a6adc8;
                font-size: 12px;
                padding: 4px 0;
            }
        """)
        progress_layout.addWidget(self.lbl_progress)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(130)
        self.txt_log.setFont(self._get_monospace_font())
        self.txt_log.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
                color: #a6adc8;
                font-size: 11px;
                padding: 8px;
            }
        """)
        progress_layout.addWidget(self.txt_log)

        layout.addWidget(progress_card)

        # 关闭按钮
        close_row = QHBoxLayout()
        close_row.addStretch()
        self.btn_close = QPushButton("关闭")
        self.btn_close.setMinimumHeight(36)
        self.btn_close.setMinimumWidth(100)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.close)
        close_row.addWidget(self.btn_close)
        layout.addLayout(close_row)

    def _get_monospace_font(self):
        font = QFont("Consolas, Microsoft YaHei", 9)
        font.setStyleHint(QFont.Monospace)
        return font

    def _refresh_index_list(self):
        """刷新已加载索引列表"""
        self.index_list.clear()
        for idx in self.search_engine.get_loaded_indexes():
            label = idx["label"]
            root = idx["root_path"]
            count = idx["total_files"]
            item = QListWidgetItem(f"  {label}  |  根目录：{root}  |  文件数：{count}")
            item.setData(Qt.UserRole, idx["path"])
            self.index_list.addItem(item)

    def _load_index(self):
        """加载索引文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择索引文件", "",
            "索引文件 (*.db);;所有文件 (*)"
        )
        if not file_path:
            return

        try:
            self.search_engine.load_index(file_path)
            self._refresh_index_list()
            self._log(f"已加载索引：{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载索引失败:\n{e}")

    def _unload_index(self):
        """卸载选中的索引"""
        current = self.index_list.currentItem()
        if not current:
            return
        db_path = current.data(Qt.UserRole)
        self.search_engine.unload_index(db_path)
        self._refresh_index_list()
        self._log(f"已卸载索引：{db_path}")

    def _browse_source(self):
        """选择扫描目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择要扫描的目录")
        if dir_path:
            self.txt_source.setEditText(dir_path)

    def _browse_save(self):
        """选择索引保存位置"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择索引保存目录")
        if dir_path:
            self.txt_save.setEditText(dir_path)

    def _start_index(self):
        """开始索引"""
        source = self.txt_source.currentText().strip()
        save_dir = self.txt_save.currentText().strip()

        if not source:
            QMessageBox.warning(self, "提示", "请选择要扫描的目录")
            return
        if not os.path.isdir(source):
            QMessageBox.warning(self, "提示", f"目录不存在：{source}")
            return
        if not save_dir:
            QMessageBox.warning(self, "提示", "请选择索引保存位置")
            return

        # 确保保存目录存在
        os.makedirs(save_dir, exist_ok=True)

        # 获取选中的文件类型
        file_types = [ext for ext, cb in self.type_checks.items() if cb.isChecked()]
        if not file_types:
            QMessageBox.warning(self, "提示", "请至少选择一种文件类型")
            return

        # 生成索引文件名
        dir_name = os.path.basename(source.rstrip("\\/"))
        if not dir_name:
            dir_name = "root"
        db_filename = f"{dir_name}_index.db"
        db_path = os.path.join(save_dir, db_filename)

        # 索引模式
        is_incremental = self.radio_incremental.isChecked()
        if not is_incremental and os.path.exists(db_path):
            reply = QMessageBox.question(
                self, "确认",
                f"索引文件已存在：{db_path}\n全量重建将覆盖此文件，确定继续？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            os.remove(db_path)

        # 启动索引线程
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.lbl_progress.setText("正在启动...")

        self.indexer_thread = IndexerThread(
            root_path=source,
            db_path=db_path,
            file_types=file_types,
            is_incremental=is_incremental
        )
        self.indexer_thread.progress.connect(self._on_progress)
        self.indexer_thread.phase_changed.connect(self._on_phase)
        self.indexer_thread.finished.connect(self._on_finished)
        self.indexer_thread.error.connect(self._on_error)
        self.indexer_thread.log_message.connect(self._log)
        self.indexer_thread.start()

    def _cancel_index(self):
        """取消索引"""
        if self.indexer_thread:
            self.indexer_thread.cancel()
            self.lbl_progress.setText("正在取消...")
            self._log("用户取消索引")

    def _on_progress(self, current, total, filename):
        """进度更新"""
        if total > 0:
            pct = int(current / total * 100)
            self.progress_bar.setValue(pct)
            self.lbl_progress.setText(f"{current}/{total} — {filename}")

    def _on_phase(self, phase):
        """阶段变化"""
        phase_names = {
            "scanning": "扫描文件...",
            "parsing": "解析内容...",
            "indexing": "构建索引...",
            "done": "完成!"
        }
        name = phase_names.get(phase, phase)
        self.lbl_progress.setText(name)

        if phase == "done":
            self.btn_start.setEnabled(True)
            self.btn_cancel.setEnabled(False)
            self.progress_bar.setValue(100)
            self._refresh_index_list()

    def _on_finished(self, total, new_count, updated_count):
        """索引完成"""
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setValue(100)
        self._log(f"索引完成：总计{total}个文件，新增{new_count}，更新{updated_count}")
        self._refresh_index_list()

        # 自动加载新创建的索引
        source = self.txt_source.currentText().strip()
        save_dir = self.txt_save.currentText().strip()
        dir_name = os.path.basename(source.rstrip("\\/"))
        db_path = os.path.join(save_dir, f"{dir_name}_index.db")
        if os.path.exists(db_path):
            try:
                self.search_engine.load_index(db_path)
                self._refresh_index_list()
            except Exception:
                pass

    def _on_error(self, error_msg):
        """索引错误"""
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        QMessageBox.critical(self, "索引错误", error_msg)
        self._log(f"错误：{error_msg}")

    def _log(self, message):
        """添加日志"""
        timestamp = time.strftime("%H:%M:%S")
        self.txt_log.append(f"[{timestamp}] {message}")
