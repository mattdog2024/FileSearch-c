"""主窗口 - 明亮暖白主题
卡片式结果列表 + Chip 筛选 + 抽屉式索引管理
"""
import os
import sys
import time
import subprocess
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QHeaderView, QSplitter, QComboBox,
    QSystemTrayIcon, QMenu, QAction, QApplication, QAbstractItemView,
    QStatusBar, QMessageBox, QShortcut, QFrame, QGraphicsDropShadowEffect,
    QListWidget, QListWidgetItem, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon, QKeySequence, QColor

from core.searcher import SearchEngine, SearchResult
from core.text_utils import format_file_size
from ui.preview_panel import PreviewPanel
from ui.index_dialog import IndexDialog


# 文件类型图标配色（设计稿定义）
FILE_TYPE_COLORS = {
    'pdf': '#DC2626',
    'doc': '#2563EB', 'docx': '#2563EB',
    'xls': '#059669', 'xlsx': '#059669',
    'ppt': '#EA580C', 'pptx': '#EA580C',
    'md': '#0891B2',
    'txt': '#64748B',
    'py': '#7C3AED', 'js': '#7C3AED', 'ts': '#7C3AED',
    'java': '#7C3AED', 'c': '#7C3AED', 'cpp': '#7C3AED',
    'css': '#7C3AED', 'html': '#DB2777', 'htm': '#DB2777',
    'json': '#B45309', 'xml': '#B45309', 'yaml': '#B45309',
}

# 类型分类映射
TYPE_CATEGORY_MAP = {
    'doc': ['.doc', '.docx', '.md', '.rtf', '.epub'],
    'sheet': ['.xls', '.xlsx', '.csv'],
    'pdf': ['.pdf'],
    'code': ['.py', '.js', '.ts', '.java', '.c', '.cpp', '.css',
             '.html', '.htm', '.json', '.xml', '.yaml', '.ini',
             '.cfg', '.sql', '.bat', '.sh', '.ps1'],
    'text': ['.txt', '.log'],
}

# 类型分类显示名
TYPE_CATEGORY_LABELS = {
    'all': '全部',
    'doc': '文档',
    'sheet': '表格',
    'pdf': 'PDF',
    'code': '代码',
    'text': '文本',
}


class SearchWorker(QThread):
    """搜索工作线程"""
    results_ready = pyqtSignal(list, float)  # results, elapsed_time

    def __init__(self, engine, query, limit=500, sort_by="relevance"):
        super().__init__()
        self.engine = engine
        self.query = query
        self.limit = limit
        self.sort_by = sort_by

    def run(self):
        t0 = time.time()
        results = self.engine.search(self.query, self.limit, self.sort_by)
        elapsed = time.time() - t0
        self.results_ready.emit(results, elapsed)


class ResultCard(QWidget):
    """结果卡片组件"""

    def __init__(self, result, keywords=None, parent=None):
        super().__init__(parent)
        self.result = result
        self._selected = False
        self._setup_ui(keywords or [])

    def _setup_ui(self, keywords):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # 文件类型图标（44x44 色块）
        ext = self.result.extension.lower().replace('.', '')
        color = FILE_TYPE_COLORS.get(ext, '#64748B')
        icon_label = QLabel(ext[:3].upper())
        icon_label.setFixedSize(44, 44)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 700;
                font-family: "Consolas", "JetBrains Mono", monospace;
            }}
        """)
        layout.addWidget(icon_label)

        # 右侧内容
        content = QVBoxLayout()
        content.setSpacing(4)

        # 标题行
        self.lbl_title = QLabel(self.result.filename)
        self.lbl_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: #1C1917;
                background: transparent;
            }
        """)
        content.addWidget(self.lbl_title)

        # 路径
        self.lbl_path = QLabel(self.result.relative_path)
        self.lbl_path.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #A8A29E;
                font-family: "Consolas", "JetBrains Mono", monospace;
                background: transparent;
            }
        """)
        content.addWidget(self.lbl_path)

        # 匹配片段
        snippet = self.result.match_snippet if hasattr(self.result, 'match_snippet') else ''
        if snippet:
            # 高亮关键词
            display_snippet = snippet
            for kw in keywords:
                display_snippet = display_snippet.replace(
                    kw,
                    f'<span style="background:#FEF3C7;color:#78350F;padding:0 2px;border-radius:2px;font-weight:500;">{kw}</span>'
                )
            self.lbl_snippet = QLabel(display_snippet)
            self.lbl_snippet.setTextFormat(Qt.RichText)
            self.lbl_snippet.setWordWrap(True)
            self.lbl_snippet.setMaximumHeight(38)
            self.lbl_snippet.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: #57534E;
                    line-height: 1.55;
                    background: transparent;
                }
            """)
            content.addWidget(self.lbl_snippet)

        # 底部元信息行
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(0)

        meta_text = f'{self.result.file_size_str}'
        sep = f'<span style="color:#D6D3D1;"> · </span>'
        meta_text += f'{sep}{self.result.modified_time_str}'

        self.lbl_meta = QLabel(meta_text)
        self.lbl_meta.setTextFormat(Qt.RichText)
        self.lbl_meta.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #A8A29E;
                background: transparent;
            }
        """)
        meta_layout.addWidget(self.lbl_meta)

        meta_layout.addStretch()

        # 索引来源 tag
        if hasattr(self.result, 'source_name') and self.result.source_name:
            source_tag = QLabel(self.result.source_name)
            source_tag.setStyleSheet("""
                QLabel {
                    background-color: #F5F5F4;
                    border-radius: 4px;
                    padding: 2px 7px;
                    font-size: 10px;
                    font-weight: 500;
                    color: #57534E;
                }
            """)
            meta_layout.addWidget(source_tag)

        content.addLayout(meta_layout)
        layout.addLayout(content, stretch=1)

        # 卡片样式
        self._update_style()

    def set_selected(self, selected):
        self._selected = selected
        self._update_style()

    def _update_style(self):
        if self._selected:
            self.setStyleSheet("""
                ResultCard {
                    background-color: #EEF2FF;
                    border: 1px solid #4F46E5;
                    border-radius: 12px;
                }
            """)
        else:
            self.setStyleSheet("""
                ResultCard {
                    background-color: #FFFFFF;
                    border: 1px solid #E7E5E4;
                    border-radius: 12px;
                }
                ResultCard:hover {
                    border-color: #D6D3D1;
                }
            """)


class ChipButton(QPushButton):
    """Chip 筛选按钮"""

    def __init__(self, text, value, count=0, parent=None):
        super().__init__(parent)
        self.value = value
        self._active = False
        self._base_text = text
        self._count = count
        self._update_text()
        self._update_style()
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(26)

    def _update_text(self):
        if self._count > 0:
            self.setText(f'{self._base_text} {self._count}')
        else:
            self.setText(self._base_text)

    def set_count(self, count):
        self._count = count
        self._update_text()

    def set_active(self, active):
        self._active = active
        self._update_style()

    def is_active(self):
        return self._active

    def _update_style(self):
        if self._active:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #EEF2FF;
                    border: 1px solid #C7D2FE;
                    border-radius: 999px;
                    padding: 5px 11px;
                    font-size: 12px;
                    font-weight: 500;
                    color: #3730A3;
                }
                QPushButton:hover {
                    border-color: #A5B4FC;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    border: 1px solid #E7E5E4;
                    border-radius: 999px;
                    padding: 5px 11px;
                    font-size: 12px;
                    font-weight: 500;
                    color: #57534E;
                }
                QPushButton:hover {
                    border-color: #A8A29E;
                }
            """)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.search_engine = SearchEngine()
        self.search_worker = None
        self.current_results = []
        self.search_history = []
        self._active_type_filter = 'all'
        self._search_elapsed = 0
        self._setup_ui()
        self._setup_tray()
        self._setup_shortcuts()
        self._load_config()

    def _setup_ui(self):
        self.setWindowTitle("FileSearch · 文件全文搜索")
        self.setMinimumSize(1200, 720)
        self.resize(1440, 960)

        # 中心部件
        central = QWidget()
        central.setObjectName("centralWidget")
        central.setStyleSheet("QWidget#centralWidget { background-color: #FAFAF9; }")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== TopBar =====
        topbar = self._build_topbar()
        main_layout.addWidget(topbar)

        # ===== 主内容区（分割器 42%/58%）=====
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：结果列表
        left_panel = self._build_results_panel()
        splitter.addWidget(left_panel)

        # 右侧：预览面板
        self.preview_panel = PreviewPanel()
        self.preview_panel.setMinimumWidth(400)
        splitter.addWidget(self.preview_panel)

        # 42% / 58% 比例
        splitter.setSizes([605, 835])
        splitter.setStretchFactor(0, 42)
        splitter.setStretchFactor(1, 58)

        main_layout.addWidget(splitter, stretch=1)

        # 搜索防抖定时器
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search)

    def _build_topbar(self):
        """构建顶部工具栏"""
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setStyleSheet("""
            QFrame#topbar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E7E5E4;
            }
        """)

        top_layout = QVBoxLayout(topbar)
        top_layout.setContentsMargins(20, 14, 20, 14)
        top_layout.setSpacing(0)

        # 第一行：Brand + SearchBox + Actions
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        # Brand
        brand = QHBoxLayout()
        brand.setSpacing(8)

        # Logo 方块
        logo = QLabel("FS")
        logo.setFixedSize(32, 32)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("""
            QLabel {
                background-color: #4F46E5;
                color: white;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 700;
            }
        """)
        brand.addWidget(logo)

        # 品牌文字
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        lbl_name = QLabel("FileSearch")
        lbl_name.setStyleSheet("""
            QLabel { font-size: 15px; font-weight: 600; color: #1C1917;
                     background: transparent; }
        """)
        brand_text.addWidget(lbl_name)
        lbl_sub = QLabel("本地全文搜索")
        lbl_sub.setStyleSheet("""
            QLabel { font-size: 11px; font-weight: 500; color: #A8A29E;
                     background: transparent; }
        """)
        brand_text.addWidget(lbl_sub)
        brand.addLayout(brand_text)

        row1.addLayout(brand)

        # 竖分隔线
        sep = QFrame()
        sep.setFixedSize(1, 32)
        sep.setStyleSheet("background-color: #E7E5E4;")
        row1.addWidget(sep)

        # SearchBox
        search_box = QWidget()
        search_box.setObjectName("searchBox")
        search_box.setStyleSheet("""
            QWidget#searchBox {
                background-color: #F5F5F4;
                border: 1.5px solid #E7E5E4;
                border-radius: 8px;
            }
            QWidget#searchBox:focus-within {
                background-color: #FFFFFF;
                border: 1.5px solid #4F46E5;
            }
        """)
        search_box.setFixedHeight(44)
        search_layout = QHBoxLayout(search_box)
        search_layout.setContentsMargins(12, 0, 12, 0)
        search_layout.setSpacing(10)

        # SEARCH 前缀标签
        prefix = QLabel("SEARCH")
        prefix.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 600;
                color: #A8A29E;
                font-family: "Consolas", "JetBrains Mono", monospace;
                background: transparent;
                border: none;
            }
        """)
        search_layout.addWidget(prefix)

        # 竖分隔线
        sep2 = QFrame()
        sep2.setFixedSize(1, 20)
        sep2.setStyleSheet("background-color: #E7E5E4; border: none;")
        search_layout.addWidget(sep2)

        # 输入框
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("搜索文件名或文件内容 …")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #1C1917;
                font-size: 15px;
                padding: 0;
            }
            QLineEdit:focus {
                border: none;
            }
        """)
        self.txt_search.textChanged.connect(self._on_search_changed)
        self.txt_search.returnPressed.connect(self._on_search_enter)
        search_layout.addWidget(self.txt_search, stretch=1)

        # 快捷键提示 kbd
        kbd_layout = QHBoxLayout()
        kbd_layout.setSpacing(4)
        for key in ["Ctrl", "K"]:
            kbd = QLabel(key)
            kbd.setAlignment(Qt.AlignCenter)
            kbd.setStyleSheet("""
                QLabel {
                    background-color: #FFFFFF;
                    border: 1px solid #D6D3D1;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 11px;
                    font-family: "Consolas", "JetBrains Mono", monospace;
                    color: #57534E;
                    min-width: 20px;
                }
            """)
            kbd_layout.addWidget(kbd)
        search_layout.addLayout(kbd_layout)

        row1.addWidget(search_box, stretch=1)

        # 操作按钮
        self.btn_index = QPushButton("索引管理")
        self.btn_index.setCursor(Qt.PointingHandCursor)
        self.btn_index.clicked.connect(self._open_index_dialog)
        row1.addWidget(self.btn_index)

        self.btn_help = QPushButton("帮助")
        self.btn_help.setObjectName("ghostBtn")
        self.btn_help.setCursor(Qt.PointingHandCursor)
        row1.addWidget(self.btn_help)

        top_layout.addLayout(row1)

        # 第二行：FilterRow
        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 12, 0, 0)
        row2.setSpacing(8)

        # 类型筛选
        lbl_type = QLabel("类型")
        lbl_type.setStyleSheet("""
            QLabel { font-size: 12px; font-weight: 500; color: #A8A29E;
                     background: transparent; }
        """)
        row2.addWidget(lbl_type)

        self.type_chips = []
        for cat in ['all', 'doc', 'sheet', 'pdf', 'code', 'text']:
            chip = ChipButton(TYPE_CATEGORY_LABELS[cat], cat)
            chip.set_active(cat == 'all')
            chip.clicked.connect(lambda checked, c=cat: self._on_type_chip_clicked(c))
            self.type_chips.append(chip)
            row2.addWidget(chip)

        # 分隔线
        sep3 = QFrame()
        sep3.setFixedSize(1, 18)
        sep3.setStyleSheet("background-color: #E7E5E4;")
        row2.addWidget(sep3)

        # 时间筛选
        lbl_time = QLabel("时间")
        lbl_time.setStyleSheet("""
            QLabel { font-size: 12px; font-weight: 500; color: #A8A29E;
                     background: transparent; }
        """)
        row2.addWidget(lbl_time)

        self.time_chips = []
        for val, label in [('recent7d', '最近 7 天'), ('thisMonth', '本月'), ('thisYear', '今年')]:
            chip = ChipButton(label, val)
            chip.clicked.connect(lambda checked, c=val: self._on_time_chip_clicked(c))
            self.time_chips.append(chip)
            row2.addWidget(chip)

        # 分隔线
        sep4 = QFrame()
        sep4.setFixedSize(1, 18)
        sep4.setStyleSheet("background-color: #E7E5E4;")
        row2.addWidget(sep4)

        # 索引源筛选
        lbl_source = QLabel("索引源")
        lbl_source.setStyleSheet("""
            QLabel { font-size: 12px; font-weight: 500; color: #A8A29E;
                     background: transparent; }
        """)
        row2.addWidget(lbl_source)

        self.source_chips = []
        # 动态生成（根据已加载的索引）
        self._update_source_chips(row2)

        row2.addStretch()

        # 排序选择
        self.cmb_sort = QComboBox()
        self.cmb_sort.addItem("按相关性排序", "relevance")
        self.cmb_sort.addItem("按修改时间", "time")
        self.cmb_sort.addItem("按文件大小", "size")
        self.cmb_sort.addItem("按文件名", "name")
        self.cmb_sort.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 999px;
                padding: 5px 11px;
                font-size: 12px;
                font-weight: 500;
                color: #57534E;
                min-width: 110px;
            }
            QComboBox:hover { border-color: #A8A29E; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox::down-arrow {
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 5px solid #57534E;
                margin-right: 4px;
            }
        """)
        self.cmb_sort.currentIndexChanged.connect(self._on_filter_changed)
        row2.addWidget(self.cmb_sort)

        top_layout.addLayout(row2)

        return topbar

    def _update_source_chips(self, layout):
        """更新索引源 chips"""
        # 清除旧的
        for chip in self.source_chips:
            chip.setParent(None)
            chip.deleteLater()
        self.source_chips.clear()

        indexes = self.search_engine.get_loaded_indexes()
        for idx in indexes:
            name = idx.get('label', '未知')
            chip = ChipButton(name, name)
            chip.clicked.connect(lambda checked, c=name: self._on_source_chip_clicked(c))
            self.source_chips.append(chip)
            layout.addWidget(chip)

    def _build_results_panel(self):
        """构建左侧结果面板"""
        panel = QWidget()
        panel.setStyleSheet("QWidget { background-color: #FAFAF9; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 结果头部
        header = QWidget()
        header.setStyleSheet("QWidget { background-color: #FAFAF9; }")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 12)

        self.lbl_result_count = QLabel("")
        self.lbl_result_count.setTextFormat(Qt.RichText)
        self.lbl_result_count.setStyleSheet("""
            QLabel { font-size: 12px; font-weight: 500; color: #57534E;
                     background: transparent; }
        """)
        header_layout.addWidget(self.lbl_result_count)

        header_layout.addStretch()

        self.lbl_elapsed = QLabel("")
        self.lbl_elapsed.setStyleSheet("""
            QLabel { font-size: 11px; color: #A8A29E;
                     font-family: "Consolas", "JetBrains Mono", monospace;
                     background: transparent; }
        """)
        header_layout.addWidget(self.lbl_elapsed)

        layout.addWidget(header)

        # 结果列表（使用 QScrollArea + 动态卡片）
        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.results_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #FAFAF9;
                border-right: 1px solid #E7E5E4;
            }
        """)

        self.results_container = QWidget()
        self.results_container.setStyleSheet("QWidget { background-color: #FAFAF9; }")
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(12, 0, 12, 12)
        self.results_layout.setSpacing(8)
        self.results_layout.addStretch()

        self.results_scroll.setWidget(self.results_container)
        layout.addWidget(self.results_scroll, stretch=1)

        # 存储卡片引用
        self._result_cards = []
        self._selected_card_index = -1

        return panel

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
        QShortcut(QKeySequence("Ctrl+K"), self, self._focus_search)
        QShortcut(QKeySequence("Escape"), self, self._clear_search)
        QShortcut(QKeySequence("Ctrl+Q"), self, self._quit_app)

    def _focus_search(self):
        """聚焦搜索框并全选"""
        self.txt_search.setFocus()
        self.txt_search.selectAll()

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
        """获取配置文件的路"""
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(app_dir, "config.ini")

    # ---- 搜索逻辑 ----

    def _on_search_changed(self, text):
        """搜索框内容变化（防抖 200ms）"""
        self._search_timer.start(200)

    def _on_search_enter(self):
        """回车键触发搜索"""
        self._search_timer.stop()
        self._do_search()

    def _on_filter_changed(self):
        """过滤条件变化"""
        self._do_search()

    def _on_type_chip_clicked(self, category):
        """类型 chip 点击（单选）"""
        self._active_type_filter = category
        for chip in self.type_chips:
            chip.set_active(chip.value == category)
        self._filter_results()

    def _on_time_chip_clicked(self, value):
        """时间 chip 点击（多选切换）"""
        for chip in self.time_chips:
            if chip.value == value:
                chip.set_active(not chip.is_active())
                break
        self._filter_results()

    def _on_source_chip_clicked(self, value):
        """索引源 chip 点击（多选切换）"""
        for chip in self.source_chips:
            if chip.value == value:
                chip.set_active(not chip.is_active())
                break
        self._filter_results()

    def _do_search(self):
        """执行搜索"""
        query = self.txt_search.text().strip()
        sort_by = self.cmb_sort.currentData()

        if query and query not in self.search_history:
            self.search_history.insert(0, query)
            self.search_history = self.search_history[:20]

        if not self.search_engine.databases:
            self.lbl_result_count.setText("⚠ 请先加载索引")
            self._clear_result_cards()
            self.current_results = []
            return

        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.quit()
            self.search_worker.wait()

        self.search_worker = SearchWorker(self.search_engine, query, sort_by=sort_by)
        self.search_worker.results_ready.connect(self._on_results_ready)
        self.search_worker.start()

    def _on_results_ready(self, results, elapsed):
        """搜索结果就绪"""
        self._search_elapsed = elapsed
        self.current_results = results
        self._update_type_chip_counts(results)
        self._filter_results()

    def _update_type_chip_counts(self, results):
        """更新类型 chip 计数"""
        counts = {'all': len(results)}
        for cat in ['doc', 'sheet', 'pdf', 'code', 'text']:
            exts = TYPE_CATEGORY_MAP.get(cat, [])
            counts[cat] = sum(1 for r in results if r.extension.lower() in exts)

        for chip in self.type_chips:
            chip.set_count(counts.get(chip.value, 0))

    def _filter_results(self):
        """根据筛选条件过滤结果"""
        filtered = self.current_results

        # 类型过滤
        if self._active_type_filter != 'all':
            exts = TYPE_CATEGORY_MAP.get(self._active_type_filter, [])
            filtered = [r for r in filtered if r.extension.lower() in exts]

        # 时间过滤
        active_times = [c.value for c in self.time_chips if c.is_active()]
        if active_times:
            import datetime
            now = datetime.datetime.now()
            if 'recent7d' in active_times:
                cutoff = now - datetime.timedelta(days=7)
                filtered = [r for r in filtered if
                            hasattr(r, 'modified_time') and r.modified_time and
                            datetime.datetime.fromtimestamp(r.modified_time) >= cutoff]
            if 'thisMonth' in active_times:
                filtered = [r for r in filtered if
                            hasattr(r, 'modified_time') and r.modified_time and
                            datetime.datetime.fromtimestamp(r.modified_time).month == now.month]
            if 'thisYear' in active_times:
                filtered = [r for r in filtered if
                            hasattr(r, 'modified_time') and r.modified_time and
                            datetime.datetime.fromtimestamp(r.modified_time).year == now.year]

        # 索引源过滤
        active_sources = [c.value for c in self.source_chips if c.is_active()]
        if active_sources:
            filtered = [r for r in filtered if
                        hasattr(r, 'source_name') and r.source_name in active_sources]

        self._populate_result_cards(filtered)

        # 更新统计
        query = self.txt_search.text().strip()
        if query:
            self.lbl_result_count.setText(
                f'<strong style="color:#1C1917;font-weight:600;">{len(filtered)}</strong> '
                f'个结果匹配「<strong style="color:#1C1917;font-weight:600;">{query}</strong>」'
            )
        else:
            self.lbl_result_count.setText(f'共 <strong style="color:#1C1917;font-weight:600;">{len(filtered)}</strong> 个文件')

        self.lbl_elapsed.setText(f'{self._search_elapsed:.2f}s')

    def _clear_result_cards(self):
        """清除所有结果卡片"""
        for card in self._result_cards:
            card.setParent(None)
            card.deleteLater()
        self._result_cards.clear()
        self._selected_card_index = -1

    def _populate_result_cards(self, results):
        """填充结果卡片"""
        self._clear_result_cards()

        query = self.txt_search.text().strip()
        keywords = query.split() if query else []

        for i, result in enumerate(results):
            card = ResultCard(result, keywords)
            card.mousePressEvent = lambda event, idx=i: self._on_card_clicked(idx)
            card.mouseDoubleClickEvent = lambda event, idx=i: self._on_card_double_clicked(idx)
            self._result_cards.append(card)
            # 插入到 stretch 之前
            self.results_layout.insertWidget(self.results_layout.count() - 1, card)

        # 自动选中第一个
        if results:
            self._on_card_clicked(0)

    def _on_card_clicked(self, index):
        """卡片点击"""
        # 更新选中状态
        for i, card in enumerate(self._result_cards):
            card.set_selected(i == index)
        self._selected_card_index = index

        # 更新预览
        if index < len(self.current_results):
            result = self.current_results[index]
            query = self.txt_search.text().strip()
            keywords = query.split() if query else []
            self.preview_panel.show_file(result, keywords)

    def _on_card_double_clicked(self, index):
        """双击打开文件"""
        if index >= len(self.current_results):
            return

        result = self.current_results[index]
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
        """打开索引管理抽屉"""
        if not hasattr(self, '_index_drawer'):
            self._index_drawer = IndexDialog(self.search_engine, self)
        self._index_drawer.show_drawer()
        # 搜索结束后刷新
        self._update_index_info()

    def _update_index_info(self):
        """更新索引信息"""
        indexes = self.search_engine.get_loaded_indexes()
        # 更新 source chips
        # 找到 filter row 中 source chips 所在的 layout
        # 简单处理：在需要时重建
        pass

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
