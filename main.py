"""FileSearch - 文件全文搜索索引工具
入口文件 - 现代化界面
"""
import sys
import os

# ---- 中文编码修复（Windows 打包后关键）----
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# PyInstaller 打包后的路径处理
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.abspath(__file__))

if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from ui.main_window import MainWindow


def main():
    # 高DPI支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # 设置全局字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    # 设置应用信息
    app.setApplicationName("FileSearch")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("FileSearch")

    # 设置现代化样式
    app.setStyleSheet(get_stylesheet())

    # 创建主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


def get_stylesheet():
    """现代化深色主题样式表"""
    return """
    /* ===== 全局 ===== */
    QMainWindow {
        background-color: #1e1e2e;
    }

    QWidget {
        color: #cdd6f4;
        font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    }

    /* ===== 输入框 ===== */
    QLineEdit {
        background-color: #313244;
        border: 1px solid #45475a;
        border-radius: 8px;
        padding: 8px 14px;
        color: #cdd6f4;
        selection-background-color: #89b4fa;
        selection-color: #1e1e2e;
    }

    QLineEdit:focus {
        border-color: #89b4fa;
    }

    QLineEdit:hover {
        border-color: #585b70;
    }

    /* ===== 按钮 ===== */
    QPushButton {
        background-color: #313244;
        border: 1px solid #45475a;
        border-radius: 8px;
        padding: 7px 18px;
        color: #cdd6f4;
        min-height: 22px;
    }

    QPushButton:hover {
        background-color: #45475a;
        border-color: #585b70;
    }

    QPushButton:pressed {
        background-color: #585b70;
    }

    QPushButton#primaryBtn {
        background-color: #89b4fa;
        color: #1e1e2e;
        border: none;
        font-weight: bold;
    }

    QPushButton#primaryBtn:hover {
        background-color: #74c7ec;
    }

    QPushButton#primaryBtn:pressed {
        background-color: #89dceb;
    }

    QPushButton#dangerBtn {
        background-color: #f38ba8;
        color: #1e1e2e;
        border: none;
        font-weight: bold;
    }

    QPushButton#dangerBtn:hover {
        background-color: #eba0ac;
    }

    QPushButton#successBtn {
        background-color: #a6e3a1;
        color: #1e1e2e;
        border: none;
        font-weight: bold;
    }

    QPushButton#successBtn:hover {
        background-color: #94e2d5;
    }

    /* ===== 下拉框 ===== */
    QComboBox {
        background-color: #313244;
        border: 1px solid #45475a;
        border-radius: 8px;
        padding: 6px 12px;
        color: #cdd6f4;
        min-width: 90px;
    }

    QComboBox:hover {
        border-color: #89b4fa;
    }

    QComboBox::drop-down {
        border: none;
        width: 24px;
    }

    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid #cdd6f4;
        margin-right: 6px;
    }

    QComboBox QAbstractItemView {
        background-color: #313244;
        border: 1px solid #45475a;
        border-radius: 4px;
        color: #cdd6f4;
        selection-background-color: #45475a;
        selection-color: #cdd6f4;
        outline: none;
    }

    /* ===== 表格 ===== */
    QTableWidget {
        background-color: #1e1e2e;
        alternate-background-color: #181825;
        border: 1px solid #313244;
        border-radius: 8px;
        gridline-color: #313244;
        selection-background-color: #313244;
        selection-color: #cdd6f4;
        outline: none;
    }

    QTableWidget::item {
        padding: 6px 10px;
        border-bottom: 1px solid #313244;
    }

    QTableWidget::item:selected {
        background-color: #45475a;
        color: #cdd6f4;
    }

    QTableWidget::item:hover {
        background-color: #313244;
    }

    QHeaderView::section {
        background-color: #181825;
        border: none;
        border-bottom: 2px solid #45475a;
        border-right: 1px solid #313244;
        padding: 8px 10px;
        color: #a6adc8;
        font-weight: 600;
        font-size: 12px;
    }

    QHeaderView::section:hover {
        background-color: #313244;
        color: #cdd6f4;
    }

    QTableWidget QScrollBar:vertical {
        background-color: #1e1e2e;
        width: 8px;
        border-radius: 4px;
    }

    QTableWidget QScrollBar::handle:vertical {
        background-color: #45475a;
        border-radius: 4px;
        min-height: 30px;
    }

    QTableWidget QScrollBar::handle:vertical:hover {
        background-color: #585b70;
    }

    QTableWidget QScrollBar::add-line:vertical,
    QTableWidget QScrollBar::sub-line:vertical {
        height: 0px;
    }

    /* ===== 分组框 ===== */
    QGroupBox {
        font-weight: 600;
        border: 1px solid #313244;
        border-radius: 10px;
        margin-top: 12px;
        padding: 20px 12px 12px 12px;
        background-color: #181825;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 8px;
        color: #89b4fa;
    }

    /* ===== 进度条 ===== */
    QProgressBar {
        border: none;
        border-radius: 6px;
        text-align: center;
        background-color: #313244;
        color: #cdd6f4;
        height: 12px;
        font-size: 11px;
    }

    QProgressBar::chunk {
        background-color: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 #89b4fa, stop:1 #74c7ec
        );
        border-radius: 6px;
    }

    /* ===== 列表 ===== */
    QListWidget {
        background-color: #181825;
        border: 1px solid #313244;
        border-radius: 8px;
        color: #cdd6f4;
        outline: none;
    }

    QListWidget::item {
        padding: 6px 10px;
        border-radius: 4px;
        margin: 2px 4px;
    }

    QListWidget::item:selected {
        background-color: #45475a;
        color: #cdd6f4;
    }

    QListWidget::item:hover {
        background-color: #313244;
    }

    /* ===== 文本编辑 ===== */
    QTextEdit {
        background-color: #181825;
        border: 1px solid #313244;
        border-radius: 8px;
        color: #cdd6f4;
        padding: 8px;
    }

    /* ===== 分割器 ===== */
    QSplitter::handle {
        background-color: #313244;
        width: 2px;
    }

    QSplitter::handle:hover {
        background-color: #89b4fa;
    }

    /* ===== 状态栏 ===== */
    QStatusBar {
        background-color: #181825;
        border-top: 1px solid #313244;
        color: #a6adc8;
        padding: 4px 12px;
    }

    QStatusBar QLabel {
        color: #a6adc8;
        padding: 2px 8px;
    }

    /* ===== 单选/复选 ===== */
    QRadioButton, QCheckBox {
        spacing: 8px;
        color: #cdd6f4;
    }

    QRadioButton::indicator, QCheckBox::indicator {
        width: 16px;
        height: 16px;
    }

    /* ===== 滚动条（通用） ===== */
    QScrollBar:vertical {
        background-color: #181825;
        width: 8px;
        border-radius: 4px;
    }

    QScrollBar::handle:vertical {
        background-color: #45475a;
        border-radius: 4px;
        min-height: 30px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #585b70;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    QScrollBar:horizontal {
        background-color: #181825;
        height: 8px;
        border-radius: 4px;
    }

    QScrollBar::handle:horizontal {
        background-color: #45475a;
        border-radius: 4px;
        min-width: 30px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: #585b70;
    }

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }

    /* ===== 标签页 ===== */
    QTabWidget::pane {
        border: 1px solid #313244;
        border-radius: 8px;
        background-color: #1e1e2e;
    }

    QTabBar::tab {
        background-color: #181825;
        border: 1px solid #313244;
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 8px 16px;
        margin-right: 2px;
        color: #a6adc8;
    }

    QTabBar::tab:selected {
        background-color: #1e1e2e;
        color: #89b4fa;
        border-bottom: 2px solid #89b4fa;
    }

    QTabBar::tab:hover {
        background-color: #313244;
        color: #cdd6f4;
    }

    /* ===== 工具提示 ===== */
    QToolTip {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #45475a;
        border-radius: 4px;
        padding: 4px 8px;
    }

    /* ===== 菜单 ===== */
    QMenu {
        background-color: #313244;
        border: 1px solid #45475a;
        border-radius: 8px;
        padding: 4px;
    }

    QMenu::item {
        padding: 6px 24px;
        border-radius: 4px;
        color: #cdd6f4;
    }

    QMenu::item:selected {
        background-color: #45475a;
    }

    QMenu::separator {
        height: 1px;
        background-color: #45475a;
        margin: 4px 8px;
    }
    """


if __name__ == "__main__":
    main()
