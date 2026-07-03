"""主窗口 - 现代化搜索界面
深色主题 + 卡片式布局 + 多索引支持 - 精致版
"""
import os
import sys
import time
import subprocess
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QComboBox, QSystemTrayIcon, QMenu,
    QAction, QApplication, QAbstractItemView, QStatusBar,
    QMessageBox, QShortcut, QFrame, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation
from PyQt5.QtGui import QFont, QIcon, QKeySequence, QColor

from core.searcher import SearchEngine, SearchResult
from core.text_utils import format_file_size
from ui.preview_panel import PreviewPanel
from ui.index_dialog import IndexDialog


class SearchWorker(QThread):
    """搜索工作线程"""
    results_ready = pyqtSignal(list)

    def __init__(self, engine, query, limit=500, sort_by="relevance"):
        super().__init__()
        self.engine = engine
        self.query = query
        self.limit = limit
        self.sort_by = sort_by

    def run(self):
        results = self.engine.search(self.query, self.limit, self.sort_by)
        self.results_ready.emit(results)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.search_engine = SearchEngine()
        self.search_worker = None
        self.current_results = []
        self.search_history = []
        self._setup_ui()
        self._setup_tray()
        self._setup_shortcuts()
        self._load_config()

    def _setup_ui(self):
        self.setWindowTitle("FileSearch · 文件全文搜索")
        self.setMinimumSize(1200, 750)
        self.resize(1400, 850)

        # 中心部件
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 16, 20, 12)
        main_layout.setSpacing(12)

        # ---- 顶部标题栏 ----
        header_layout = QHBoxLayout()

        title_label = QLabel("FileSearch")
        title_label.setObjectName("appTitle")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                padding: 4px 0;
            }
        """)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # 索引状态标签
        self.lbl_index_badge = QLabel("未加载索引")
        self.lbl_index_badge.setObjectName("indexBadge")
        self.lbl_index_badge.setStyleSheet("""
            QLabel {
                background-color: #313244;
                color: #a6adc8;
                border-radius: 14px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        header_layout.addWidget(self.lbl_index_badge)

        # 索引管理按钮
        self.btn_index = QPushButton("索引管理")
        self.btn_index.setObjectName("primaryBtn")
        self.btn_index.setMinimumHeight(38)
        self.btn_index.setMinimumWidth(110)
        self.btn_index.setCursor(Qt.PointingHandCursor)
        self.btn_index.clicked.connect(self._open_index_dialog)
        header_layout.addWidget(self.btn_index)

        main_layout.addLayout(header_layout)

        # ---- 搜索栏 ----
        search_container = QWidget()
        search_container.setObjectName("searchContainer")
        search_container.setStyleSheet("""
            QWidget#searchContainer {
                background-color: #181825;
                border-radius: 14px;
                padding: 6px;
            }
        """)
        # 添加阴影
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        search_container.setGraphicsEffect(shadow)

        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(12, 6, 12, 6)
        search_layout.setSpacing(10)

        # 搜索图标
        search_icon = QLabel("🔎")
        search_icon.setStyleSheet("font-size: 20px; color: #585b70;")
        search_layout.addWidget(search_icon)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("搜索文件内容或文件名... (空格分隔多关键词，* 通配符)")
        self.txt_search.setFont(QFont("Microsoft YaHei", 12))
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                color: #cdd6f4;
                padding: 8px 6px;
                font-size: 13px;
            }
            QLineEdit:focus {
                outline: none;
            }
        """)
        self.txt_search.textChanged.connect(self._on_search_changed)
        self.txt_search.returnPressed.connect(self._on_search_enter)
        search_layout.addWidget(self.txt_search, stretch=1)

        # 文件类型过滤
        self.cmb_ext_filter = QComboBox()
        self.cmb_ext_filter.addItem("全部类型", "all")
        for ext in [".doc", ".docx", ".xls", ".xlsx", ".pdf", ".ppt", ".pptx"]:
            self.cmb_ext_filter.addItem(ext.upper(), ext)
        self.cmb_ext_filter.setMinimumHeight(36)
        self.cmb_ext_filter.setMinimumWidth(110)
        self.cmb_ext_filter.setStyleSheet("""
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
        self.cmb_ext_filter.currentIndexChanged.connect(self._on_filter_changed)
        search_layout.addWidget(self.cmb_ext_filter)

        # 排序
        self.cmb_sort = QComboBox()
        self.cmb_sort.addItem("相关度", "relevance")
        self.cmb_sort.addItem("时间", "time")
        self.cmb_sort.addItem("大小", "size")
        self.cmb_sort.addItem("名称", "name")
        self.cmb_sort.setMinimumHeight(36)
        self.cmb_sort.setMinimumWidth(100)
        self.cmb_sort.setStyleSheet("""
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
        self.cmb_sort.currentIndexChanged.connect(self._on_filter_changed)
        search_layout.addWidget(self.cmb_sort)

        main_layout.addWidget(search_container)

        # ---- 结果统计栏 ----
        stats_layout = QHBoxLayout()

        self.lbl_result_count = QLabel("")
        self.lbl_result_count.setStyleSheet("""
            QLabel {
                color: #a6adc8;
                font-size: 12px;
                padding: 4px 0;
            }
        """)
        stats_layout.addWidget(self.lbl_result_count)

        stats_layout.addStretch()

        self.lbl_index_detail = QLabel("")
        self.lbl_index_detail.setStyleSheet("""
            QLabel {
                color: #585b70;
                font-size: 11px;
                padding: 4px 0;
            }
        """)
        stats_layout.addWidget(self.lbl_index_detail)

        main_layout.addLayout(stats_layout)

        # ---- 主内容区（分割器）----
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：结果列表
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(["文件名", "路径", "类型", "大小", "修改时间"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.result_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.result_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setShowGrid(False)
        self.result_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.result_table.cellDoubleClicked.connect(self._on_double_click)
        self.result_table.setStyleSheet("""
            QTableWidget {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 12px;
                color: #cdd6f4;
                font-size: 12px;
                gridline-color: #313244;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #313244;
            }
            QTableWidget::item:selected {
                background-color: #313244;
            }
            QHeaderView::section {
                background-color: #1e1e2e;
                color: #a6adc8;
                border: none;
                border-bottom: 2px solid #313244;
                padding: 10px 8px;
                font-weight: 600;
                font-size: 12px;
            }
            QTableWidget QScrollBar:vertical {
                background-color: #1e1e2e;
                width: 10px;
                border-radius: 5px;
            }
            QTableWidget QScrollBar::handle:vertical {
                background-color: #585b70;
                border-radius: 5px;
                min-height: 30px;
            }
            QTableWidget QScrollBar::handle:vertical:hover {
                background-color: #89b4fa;
            }
        """)
        table_layout.addWidget(self.result_table)

        splitter.addWidget(table_container)

        # 右侧：预览面板
        self.preview_panel = PreviewPanel()
        self.preview_panel.setMinimumWidth(320)
        splitter.addWidget(self.preview_panel)

        splitter.setSizes([800, 450])
        main_layout.addWidget(splitter, stretch=1)

        # 搜索防抖定时器
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search)

    def _setup_tray(self):
        """设置系统托盘"""
        self.tray_icon = QSystemTrayIcon(self)

        if getattr(sys, 'frozen', False):
            icon_base = os.path.dirname(sys.executable)
        else:
            icon_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(icon_base, "icon.ico")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))

        tray_menu = QMenu()

        show_action = QAction("显示窗口", self)
        show_action.triggered.connect(self._show_from_tray)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _setup_shortcuts(self):
        """设置快捷键"""
        QShortcut(QKeySequence("Ctrl+F"), self, self.txt_search.setFocus)
        QShortcut(QKeySequence("Escape"), self, self._clear_search)
        QShortcut(QKeySequence("Ctrl+Q"), self, self._quit_app)

    def _load_config(self):
        """加载配置"""
        config_path = self._get_config_path()
        if os.path.exists(config_path):
            try:
                import configparser
                config = configparser.ConfigParser()
                config.read(config_path, encoding="utf-8")

                if config.has_section("auto_load"):
                    for key in config.options("auto_load"):
                        db_path = config.get("auto_load", key)
                        if os.path.exists(db_path):
                            try:
                                self.search_engine.load_index(db_path)
                            except Exception:
                                pass

                if config.has_section("search_history"):
                    self.search_history = [
                        config.get("search_history", f"h{i}")
                        for i in range(20)
                        if config.has_option("search_history", f"h{i}")
                    ]

                self._update_index_info()
            except Exception:
                pass

    def _save_config(self):
        """保存配置"""
        config_path = self._get_config_path()
        try:
            import configparser
            config = configparser.ConfigParser()

            config.add_section("auto_load")
            for i, idx in enumerate(self.search_engine.get_loaded_indexes()):
                config.set("auto_load", f"idx{i}", idx["path"])

            config.add_section("search_history")
            for i, h in enumerate(self.search_history[:20]):
                config.set("search_history", f"h{i}", h)

            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                config.write(f)
        except Exception:
            pass

    def _get_config_path(self):
        """获取配置文件路径"""
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(app_dir, "config.ini")

    # ---- 搜索逻辑 ----

    def _on_search_changed(self, text):
        """搜索框内容变化（防抖）"""
        self._search_timer.start(300)

    def _on_search_enter(self):
        """回车键触发搜索"""
        self._search_timer.stop()
        self._do_search()

    def _on_filter_changed(self):
        """过滤条件变化"""
        self._do_search()

    def _do_search(self):
        """执行搜索"""
        query = self.txt_search.text().strip()
        sort_by = self.cmb_sort.currentData()

        if query and query not in self.search_history:
            self.search_history.insert(0, query)
            self.search_history = self.search_history[:20]

        if not self.search_engine.databases:
            self.lbl_result_count.setText("⚠ 请先加载索引")
            self.result_table.setRowCount(0)
            self.current_results = []
            return

        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.quit()
            self.search_worker.wait()

        self.search_worker = SearchWorker(self.search_engine, query, sort_by=sort_by)
        self.search_worker.results_ready.connect(self._on_results_ready)
        self.search_worker.start()

    def _on_results_ready(self, results):
        """搜索结果就绪"""
        ext_filter = self.cmb_ext_filter.currentData()
        if ext_filter != "all":
            results = [r for r in results if r.extension.lower() == ext_filter]

        self.current_results = results
        self._populate_results(results)

        query = self.txt_search.text().strip()
        if query:
            self.lbl_result_count.setText(f"找到 {len(results)} 个结果")
        else:
            self.lbl_result_count.setText(f"共 {len(results)} 个文件")

    def _populate_results(self, results):
        """填充结果表格"""
        self.result_table.setRowCount(len(results))

        for row, result in enumerate(results):
            # 文件名
            item_name = QTableWidgetItem(result.filename)
            item_name.setData(Qt.UserRole, row)
            if not result.is_available:
                item_name.setForeground(QColor("#585b70"))
            self.result_table.setItem(row, 0, item_name)

            # 路径
            item_path = QTableWidgetItem(result.relative_path)
            if not result.is_available:
                item_path.setForeground(QColor("#585b70"))
            self.result_table.setItem(row, 1, item_path)

            # 类型
            item_ext = QTableWidgetItem(result.extension.upper().replace(".", ""))
            item_ext.setForeground(QColor("#89b4fa"))
            self.result_table.setItem(row, 2, item_ext)

            # 大小
            item_size = QTableWidgetItem(result.file_size_str)
            self.result_table.setItem(row, 3, item_size)

            # 修改时间
            item_time = QTableWidgetItem(result.modified_time_str)
            self.result_table.setItem(row, 4, item_time)

    def _on_selection_changed(self):
        """选择变化时更新预览"""
        selected = self.result_table.selectionModel().selectedRows()
        if not selected:
            self.preview_panel.clear()
            return

        row = selected[0].row()
        if row < len(self.current_results):
            result = self.current_results[row]
            query = self.txt_search.text().strip()
            keywords = query.split() if query else []

            # 使用 result 自带的 root_path（修复多索引 bug）
            self.preview_panel.show_file(result, keywords)

    def _on_double_click(self, row, col):
        """双击打开文件"""
        if row >= len(self.current_results):
            return

        result = self.current_results[row]
        full_path = result.full_path

        if os.path.exists(full_path):
            if sys.platform == "win32":
                os.startfile(full_path)
            else:
                subprocess.Popen(["xdg-open", full_path])
        else:
            QMessageBox.information(
                self, "文件不可用",
                f"文件所在硬盘可能未连接。\n\n路径：{full_path}\n\n"
                f"索引中保存的内容仍可在右侧预览面板查看。"
            )

    def _clear_search(self):
        """清空搜索"""
        self.txt_search.clear()
        self.preview_panel.clear()

    # ---- 索引管理 ----

    def _open_index_dialog(self):
        """打开索引管理对话框"""
        dialog = IndexDialog(self.search_engine, self)
        dialog.exec_()
        self._update_index_info()
        self._do_search()

    def _update_index_info(self):
        """更新索引信息状态"""
        indexes = self.search_engine.get_loaded_indexes()
        if not indexes:
            self.lbl_index_badge.setText("⚠ 未加载索引")
            self.lbl_index_badge.setStyleSheet("""
                QLabel {
                    background-color: #45475a;
                    color: #f38ba8;
                    border-radius: 14px;
                    padding: 6px 16px;
                    font-size: 12px;
                    font-weight: 500;
                }
            """)
            self.lbl_index_detail.setText("")
            return

        total_files = sum(idx["total_files"] for idx in indexes)
        total_size = sum(idx["index_size"] for idx in indexes)
        names = [idx["label"] for idx in indexes]

        self.lbl_index_badge.setText(f"✓ {len(indexes)} 个索引 · {total_files} 文件")
        self.lbl_index_badge.setStyleSheet("""
            QLabel {
                background-color: #313244;
                color: #a6e3a1;
                border-radius: 14px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        self.lbl_index_detail.setText(
            f"{', '.join(names)} · 索引大小：{format_file_size(total_size)}"
        )

    # ---- 系统托盘 ----

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self):
        self.show()
        self.showNormal()
        self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "FileSearch",
            "程序已最小化到系统托盘，双击图标恢复",
            QSystemTrayIcon.Information,
            2000
        )

    def _quit_app(self):
        self._save_config()
        self.search_engine.close()
        self.tray_icon.hide()
        QApplication.quit()
