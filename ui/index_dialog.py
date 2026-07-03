"""索引管理抽屉 - 明亮暖白主题
右侧滑出抽屉，520px 宽，250ms 动画
"""
import os
import sys
import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QCheckBox, QProgressBar, QTextEdit,
    QComboBox, QMessageBox, QFrame, QGraphicsDropShadowEffect,
    QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from core.indexer import IndexerThread
from core.parsers import get_supported_extensions


class TypeCheckLabel(QLabel):
    """TypeCheck 标签（可点击切换）"""

    def __init__(self, ext, parent=None):
        super().__init__(ext.upper().replace(".", ""), parent)
        self.ext = ext
        self._active = True
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(28)
        self.setMinimumWidth(48)
        self._update_style()

    def _update_style(self):
        if self._active:
            self.setStyleSheet("""
                QLabel {
                    background-color: #EEF2FF;
                    border: 1px solid #C7D2FE;
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: 600;
                    font-family: "Consolas", "JetBrains Mono", monospace;
                    color: #3730A3;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    background-color: #FFFFFF;
                    border: 1px solid #E7E5E4;
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-family: "Consolas", "JetBrains Mono", monospace;
                    color: #57534E;
                }
            """)

    def mousePressEvent(self, event):
        self._active = not self._active
        self._update_style()
        super().mousePressEvent(event)

    def is_active(self):
        return self._active


class IndexDialog(QWidget):
    """索引管理抽屉（从右侧滑出）"""

    def __init__(self, search_engine, parent=None):
        super().__init__(parent)
        self.search_engine = search_engine
        self.indexer_thread = None
        self._is_open = False
        self._setup_ui()
        self._refresh_index_list()

    def _setup_ui(self):
        # 抽屉容器 - 绝对定位在父窗口右侧
        self.setFixedWidth(520)
        self.setStyleSheet("QWidget { background-color: #FFFFFF; }")

        # 阴影
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(28, 25, 23, 26))
        shadow.setOffset(-8, 0)
        self.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== DrawerHeader =====
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E7E5E4;
            }
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 20, 24, 16)
        header_layout.setSpacing(4)

        title_row = QHBoxLayout()
        lbl_title = QLabel("索引管理")
        lbl_title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 700;
                color: #1C1917;
                background: transparent;
            }
        """)
        title_row.addWidget(lbl_title)
        title_row.addStretch()

        # 关闭按钮
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                color: #57534E;
            }
            QPushButton:hover {
                background-color: #F5F5F4;
            }
        """)
        self.btn_close.clicked.connect(self.hide_drawer)
        title_row.addWidget(self.btn_close)

        header_layout.addLayout(title_row)

        lbl_subtitle = QLabel("管理已建立的搜索索引，或创建新的扫描任务")
        lbl_subtitle.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #A8A29E;
                background: transparent;
            }
        """)
        header_layout.addWidget(lbl_subtitle)

        main_layout.addWidget(header)

        # ===== DrawerBody =====
        body_scroll = QScrollArea()
        body_scroll.setWidgetResizable(True)
        body_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #FFFFFF;
            }
        """)

        body = QWidget()
        body.setStyleSheet("QWidget { background-color: #FFFFFF; }")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 20, 24, 20)
        body_layout.setSpacing(20)

        # Section 1: 已加载的索引
        section1_title = QLabel("已加载的索引")
        section1_title.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: 600;
                color: #A8A29E;
                background: transparent;
            }
        """)
        body_layout.addWidget(section1_title)

        self.index_cards_container = QVBoxLayout()
        self.index_cards_container.setSpacing(8)
        body_layout.addLayout(self.index_cards_container)

        # 加载/卸载按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_load = QPushButton("加载索引")
        self.btn_load.setObjectName("primaryBtn")
        self.btn_load.setFixedHeight(30)
        self.btn_load.setCursor(Qt.PointingHandCursor)
        self.btn_load.clicked.connect(self._load_index)
        btn_row.addWidget(self.btn_load)

        self.btn_unload = QPushButton("卸载选中")
        self.btn_unload.setObjectName("dangerBtn")
        self.btn_unload.setFixedHeight(30)
        self.btn_unload.setCursor(Qt.PointingHandCursor)
        self.btn_unload.clicked.connect(self._unload_index)
        btn_row.addWidget(self.btn_unload)

        btn_row.addStretch()
        body_layout.addLayout(btn_row)

        # Section 2: 创建新索引（虚线边框容器）
        section2_title = QLabel("创建新索引")
        section2_title.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: 600;
                color: #A8A29E;
                background: transparent;
            }
        """)
        body_layout.addWidget(section2_title)

        form_container = QFrame()
        form_container.setStyleSheet("""
            QFrame {
                background-color: #F5F5F4;
                border: 1.5px dashed #D6D3D1;
                border-radius: 8px;
            }
        """)
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(12)

        # 索引名称
        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        lbl_name = QLabel("索引名称")
        lbl_name.setFixedWidth(80)
        lbl_name.setStyleSheet("""
            QLabel { font-size: 12px; font-weight: 500; color: #57534E;
                     background: transparent; }
        """)
        name_row.addWidget(lbl_name)

        from PyQt5.QtWidgets import QLineEdit
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("例如：工作文档")
        self.txt_name.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #D6D3D1;
                border-radius: 6px;
                padding: 8px 10px;
                color: #1C1917;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #4F46E5;
            }
        """)
        name_row.addWidget(self.txt_name)
        form_layout.addLayout(name_row)

        # 扫描目录
        dir_row = QHBoxLayout()
        dir_row.setSpacing(6)
        lbl_dir = QLabel("扫描目录")
        lbl_dir.setFixedWidth(80)
        lbl_dir.setStyleSheet("""
            QLabel { font-size: 12px; font-weight: 500; color: #57534E;
                     background: transparent; }
        """)
        dir_row.addWidget(lbl_dir)

        self.txt_source = QLineEdit()
        self.txt_source.setPlaceholderText("选择要扫描的目录")
        self.txt_source.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #D6D3D1;
                border-radius: 6px;
                padding: 8px 10px;
                color: #1C1917;
                font-size: 12px;
            }
            QLineEdit:focus { border-color: #4F46E5; }
        """)
        dir_row.addWidget(self.txt_source, stretch=1)

        self.btn_browse_source = QPushButton("浏览…")
        self.btn_browse_source.setFixedHeight(32)
        self.btn_browse_source.setCursor(Qt.PointingHandCursor)
        self.btn_browse_source.clicked.connect(self._browse_source)
        dir_row.addWidget(self.btn_browse_source)
        form_layout.addLayout(dir_row)

        # 索引保存路径
        save_row = QHBoxLayout()
        save_row.setSpacing(6)
        lbl_save = QLabel("保存路径")
        lbl_save.setFixedWidth(80)
        lbl_save.setStyleSheet("""
            QLabel { font-size: 12px; font-weight: 500; color: #57534E;
                     background: transparent; }
        """)
        save_row.addWidget(lbl_save)

        self.txt_save = QLineEdit()
        self.txt_save.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #D6D3D1;
                border-radius: 6px;
                padding: 8px 10px;
                color: #1C1917;
                font-size: 12px;
                font-family: "Consolas", "JetBrains Mono", monospace;
            }
            QLineEdit:focus { border-color: #4F46E5; }
        """)
        # 默认路径
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.txt_save.setText(os.path.join(app_dir, "indexes"))
        save_row.addWidget(self.txt_save, stretch=1)

        self.btn_browse_save = QPushButton("浏览…")
        self.btn_browse_save.setFixedHeight(32)
        self.btn_browse_save.setCursor(Qt.PointingHandCursor)
        self.btn_browse_save.clicked.connect(self._browse_save)
        save_row.addWidget(self.btn_browse_save)
        form_layout.addLayout(save_row)

        # 文件类型选择（TypeCheck 标签网格）
        type_label = QLabel("包含的文件类型")
        type_label.setStyleSheet("""
            QLabel { font-size: 12px; font-weight: 500; color: #57534E;
                     background: transparent; }
        """)
        form_layout.addWidget(type_label)

        type_grid = QHBoxLayout()
        type_grid.setSpacing(6)
        self.type_checks = {}
        for ext in get_supported_extensions():
            tc = TypeCheckLabel(ext)
            self.type_checks[ext] = tc
            type_grid.addWidget(tc)
        type_grid.addStretch()
        form_layout.addLayout(type_grid)

        # 增量索引选项
        self.chk_incremental = QCheckBox("启用增量索引（只扫描变化的文件）")
        self.chk_incremental.setChecked(True)
        self.chk_incremental.setStyleSheet("""
            QCheckBox {
                font-size: 12px;
                color: #57534E;
                spacing: 8px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 2px solid #D6D3D1;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background-color: #4F46E5;
                border-color: #4F46E5;
            }
        """)
        form_layout.addWidget(self.chk_incremental)

        body_layout.addWidget(form_container)

        # 进度区
        self.progress_section = QWidget()
        self.progress_section.setStyleSheet("QWidget { background: transparent; }")
        progress_layout = QVBoxLayout(self.progress_section)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 6px;
                background-color: #E7E5E4;
            }
            QProgressBar::chunk {
                background-color: #4F46E5;
                border-radius: 6px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        self.lbl_progress = QLabel("就绪")
        self.lbl_progress.setStyleSheet("""
            QLabel { font-size: 11px; color: #A8A29E; background: transparent; }
        """)
        progress_layout.addWidget(self.lbl_progress)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(120)
        self.txt_log.setFont(QFont("Consolas", 9))
        self.txt_log.setStyleSheet("""
            QTextEdit {
                background-color: #F5F5F4;
                border: 1px solid #E7E5E4;
                border-radius: 6px;
                color: #57534E;
                font-size: 11px;
                padding: 8px;
            }
        """)
        progress_layout.addWidget(self.txt_log)

        self.progress_section.setVisible(False)
        body_layout.addWidget(self.progress_section)

        body_layout.addStretch()

        body_scroll.setWidget(body)
        main_layout.addWidget(body_scroll, stretch=1)

        # ===== DrawerFooter =====
        footer = QFrame()
        footer.setStyleSheet("""
            QFrame {
                background-color: #F5F5F4;
                border-top: 1px solid #E7E5E4;
            }
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 14, 24, 14)

        lbl_hint = QLabel("索引在后台构建，可随时使用其他索引搜索")
        lbl_hint.setStyleSheet("""
            QLabel { font-size: 11px; color: #A8A29E; background: transparent; }
        """)
        footer_layout.addWidget(lbl_hint)

        footer_layout.addStretch()

        self.btn_cancel_index = QPushButton("取消")
        self.btn_cancel_index.setFixedHeight(30)
        self.btn_cancel_index.setCursor(Qt.PointingHandCursor)
        self.btn_cancel_index.setEnabled(False)
        self.btn_cancel_index.clicked.connect(self._cancel_index)
        footer_layout.addWidget(self.btn_cancel_index)

        self.btn_start = QPushButton("开始索引")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setFixedHeight(30)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self._start_index)
        footer_layout.addWidget(self.btn_start)

        main_layout.addWidget(footer)

    def show_drawer(self):
        """显示抽屉（滑入动画）"""
        parent = self.parent()
        if not parent:
            return

        self._refresh_index_list()

        # 设置抽屉高度与父窗口一致
        self.setFixedHeight(parent.height())

        # 显示遮罩层
        if hasattr(parent, '_drawer_overlay') and parent._drawer_overlay:
            parent._drawer_overlay.setGeometry(parent.rect())
            parent._drawer_overlay.show()
            parent._drawer_overlay.raise_()

        self.show()
        self.raise_()

        # 计算目标位置：紧贴父窗口右侧内边
        target_x = parent.width() - self.width()

        # 初始位置：父窗口右侧外
        self.move(parent.width(), 0)

        # 滑入动画
        from PyQt5.QtCore import QPoint
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(250)
        self._anim.setStartValue(QPoint(parent.width(), 0))
        self._anim.setEndValue(QPoint(target_x, 0))
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

        self._is_open = True

    def hide_drawer(self):
        """隐藏抽屉（滑出动画）"""
        parent = self.parent()
        if not parent:
            self.hide()
            return

        # 隐藏遮罩层
        if hasattr(parent, '_drawer_overlay') and parent._drawer_overlay:
            parent._drawer_overlay.hide()

        from PyQt5.QtCore import QPoint
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(250)
        self._anim.setStartValue(self.pos())
        self._anim.setEndValue(QPoint(parent.width(), 0))
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._on_hide_finished)
        self._anim.start()
        self._is_open = False

    def _on_hide_finished(self):
        """动画结束后隐藏widget"""
        self.hide()

    def exec_(self):
        """兼容 QDialog.exec_ 的调用方式"""
        self.show_drawer()

    def _refresh_index_list(self):
        """刷新已加载索引列表"""
        # 清除旧卡片
        while self.index_cards_container.count():
            item = self.index_cards_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        indexes = self.search_engine.get_loaded_indexes()
        for idx in indexes:
            card = self._create_index_card(idx)
            self.index_cards_container.addWidget(card)

    def _create_index_card(self, idx):
        """创建索引卡片"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 8px;
            }
        """)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)

        # 左侧信息
        info = QVBoxLayout()
        info.setSpacing(4)

        # 名称行
        name_row = QHBoxLayout()
        name_row.setSpacing(6)

        # 状态点
        dot = QLabel("●")
        dot.setStyleSheet("""
            QLabel { font-size: 6px; color: #059669; background: transparent; }
        """)
        name_row.addWidget(dot)

        lbl_name = QLabel(idx["label"])
        lbl_name.setStyleSheet("""
            QLabel { font-size: 13px; font-weight: 600; color: #1C1917;
                     background: transparent; }
        """)
        name_row.addWidget(lbl_name)
        name_row.addStretch()
        info.addLayout(name_row)

        # 路径
        lbl_path = QLabel(idx["root_path"])
        lbl_path.setStyleSheet("""
            QLabel { font-size: 11px; color: #A8A29E;
                     font-family: "Consolas", "JetBrains Mono", monospace;
                     background: transparent; }
        """)
        info.addWidget(lbl_path)

        # 统计行
        stats_text = f'<span style="font-weight:600;color:#1C1917;">{idx["total_files"]}</span> 文件'
        lbl_stats = QLabel(stats_text)
        lbl_stats.setTextFormat(Qt.RichText)
        lbl_stats.setStyleSheet("""
            QLabel { font-size: 11px; color: #57534E; background: transparent; }
        """)
        info.addWidget(lbl_stats)

        card_layout.addLayout(info, stretch=1)

        # 右侧操作
        ops = QVBoxLayout()
        ops.setSpacing(4)

        btn_rebuild = QPushButton("重建")
        btn_rebuild.setFixedHeight(26)
        btn_rebuild.setCursor(Qt.PointingHandCursor)
        btn_rebuild.clicked.connect(lambda: self._rebuild_index(idx))
        ops.addWidget(btn_rebuild)

        btn_remove = QPushButton("移除")
        btn_remove.setObjectName("ghostBtn")
        btn_remove.setFixedHeight(26)
        btn_remove.setCursor(Qt.PointingHandCursor)
        btn_remove.clicked.connect(lambda: self._remove_index(idx))
        ops.addWidget(btn_remove)

        card_layout.addLayout(ops)

        return card

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
        # 简单实现：卸载最后一个
        indexes = self.search_engine.get_loaded_indexes()
        if indexes:
            self.search_engine.unload_index(indexes[-1]["path"])
            self._refresh_index_list()

    def _rebuild_index(self, idx):
        """重建索引"""
        self._log(f"重建索引：{idx['label']}")

    def _remove_index(self, idx):
        """移除索引"""
        reply = QMessageBox.question(
            self, "确认",
            f"确定要移除索引「{idx['label']}」？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.search_engine.unload_index(idx["path"])
            self._refresh_index_list()
            self._log(f"已移除索引：{idx['label']}")

    def _browse_source(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择要扫描的目录")
        if dir_path:
            self.txt_source.setText(dir_path)

    def _browse_save(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择索引保存目录")
        if dir_path:
            self.txt_save.setText(dir_path)

    def _start_index(self):
        """开始索引"""
        source = self.txt_source.text().strip()
        save_dir = self.txt_save.text().strip()
        name = self.txt_name.text().strip()

        if not source:
            QMessageBox.warning(self, "提示", "请选择要扫描的目录")
            return
        if not os.path.isdir(source):
            QMessageBox.warning(self, "提示", f"目录不存在：{source}")
            return
        if not save_dir:
            QMessageBox.warning(self, "提示", "请选择索引保存位置")
            return

        os.makedirs(save_dir, exist_ok=True)

        # 获取选中的文件类型
        file_types = [ext for ext, tc in self.type_checks.items() if tc.is_active()]
        if not file_types:
            QMessageBox.warning(self, "提示", "请至少选择一种文件类型")
            return

        # 生成索引文件名
        if name:
            db_filename = f"{name}_index.db"
        else:
            dir_name = os.path.basename(source.rstrip("\\/"))
            if not dir_name:
                dir_name = "root"
            db_filename = f"{dir_name}_index.db"
        db_path = os.path.join(save_dir, db_filename)

        is_incremental = self.chk_incremental.isChecked()
        if not is_incremental and os.path.exists(db_path):
            reply = QMessageBox.question(
                self, "确认",
                f"索引文件已存在：{db_path}\n全量重建将覆盖此文件，确定继续？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            os.remove(db_path)

        # 显示进度
        self.progress_section.setVisible(True)
        self.btn_start.setEnabled(False)
        self.btn_cancel_index.setEnabled(True)
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
        if self.indexer_thread:
            self.indexer_thread.cancel()
            self.lbl_progress.setText("正在取消...")
            self._log("用户取消索引")

    def _on_progress(self, current, total, filename):
        if total > 0:
            pct = int(current / total * 100)
            self.progress_bar.setValue(pct)
            self.lbl_progress.setText(f"{current}/{total} — {filename}")

    def _on_phase(self, phase):
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
            self.btn_cancel_index.setEnabled(False)
            self.progress_bar.setValue(100)
            self._refresh_index_list()

    def _on_finished(self, total, new_count, updated_count):
        self.btn_start.setEnabled(True)
        self.btn_cancel_index.setEnabled(False)
        self.progress_bar.setValue(100)
        self._log(f"索引完成：总计{total}个文件，新增{new_count}，更新{updated_count}")
        self._refresh_index_list()

        # 自动加载新索引
        source = self.txt_source.text().strip()
        save_dir = self.txt_save.text().strip()
        name = self.txt_name.text().strip()
        if name:
            db_filename = f"{name}_index.db"
        else:
            dir_name = os.path.basename(source.rstrip("\\/"))
            db_filename = f"{dir_name}_index.db"
        db_path = os.path.join(save_dir, db_filename)
        if os.path.exists(db_path):
            try:
                self.search_engine.load_index(db_path)
                self._refresh_index_list()
            except Exception:
                pass

    def _on_error(self, error_msg):
        self.btn_start.setEnabled(True)
        self.btn_cancel_index.setEnabled(False)
        QMessageBox.critical(self, "索引错误", error_msg)
        self._log(f"错误：{error_msg}")

    def _log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.txt_log.append(f"[{timestamp}] {message}")
