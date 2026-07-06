"""FileSearch - 文件全文搜索索引工具
入口文件 - 明亮暖白主题
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
    font = QFont("Microsoft YaHei UI", 9)
    app.setFont(font)

    # 设置应用信息
    app.setApplicationName("FileSearch")
    app.setApplicationVersion("2.5.0")
    app.setOrganizationName("FileSearch")

    # 设置明亮暖白主题样式
    app.setStyleSheet(get_stylesheet())

    # 创建主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


def get_stylesheet():
    """明亮暖白主题样式表 - 基于设计稿 Design Tokens"""
    return """
    /* ===== 全局 ===== */
    QMainWindow {
        background-color: #FAFAF9;
    }

    QWidget {
        color: #1C1917;
        font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    }

    /* ===== 输入框 ===== */
    QLineEdit {
        background-color: #FFFFFF;
        border: 1px solid #D6D3D1;
        border-radius: 6px;
        padding: 8px 10px;
        color: #1C1917;
        selection-background-color: #4F46E5;
        selection-color: #FFFFFF;
    }

    QLineEdit:focus {
        border-color: #4F46E5;
    }

    QLineEdit:hover {
        border-color: #A8A29E;
    }

    QLineEdit:disabled {
        background-color: #F5F5F4;
        color: #A8A29E;
    }

    /* ===== 按钮 ===== */
    QPushButton {
        background-color: #FFFFFF;
        border: 1px solid #D6D3D1;
        border-radius: 8px;
        padding: 7px 14px;
        color: #57534E;
        font-size: 13px;
        font-weight: 500;
        min-height: 22px;
    }

    QPushButton:hover {
        background-color: #F5F5F4;
        border-color: #A8A29E;
    }

    QPushButton:pressed {
        background-color: #E7E5E4;
    }

    QPushButton:disabled {
        background-color: #F5F5F4;
        color: #A8A29E;
        border-color: #E7E5E4;
    }

    QPushButton#primaryBtn {
        background-color: #4F46E5;
        color: #FFFFFF;
        border: none;
        font-weight: 600;
    }

    QPushButton#primaryBtn:hover {
        background-color: #4338CA;
    }

    QPushButton#primaryBtn:pressed {
        background-color: #3730A3;
    }

    QPushButton#primaryBtn:disabled {
        background-color: #C7D2FE;
        color: #FFFFFF;
    }

    QPushButton#dangerBtn {
        background-color: #DC2626;
        color: #FFFFFF;
        border: none;
        font-weight: 600;
    }

    QPushButton#dangerBtn:hover {
        background-color: #B91C1C;
    }

    QPushButton#ghostBtn {
        background-color: transparent;
        border: none;
        color: #57534E;
    }

    QPushButton#ghostBtn:hover {
        background-color: #F5F5F4;
    }

    /* ===== 下拉框 ===== */
    QComboBox {
        background-color: #FFFFFF;
        border: 1px solid #D6D3D1;
        border-radius: 6px;
        padding: 6px 12px;
        color: #1C1917;
        min-width: 90px;
    }

    QComboBox:hover {
        border-color: #A8A29E;
    }

    QComboBox:focus {
        border-color: #4F46E5;
    }

    QComboBox::drop-down {
        border: none;
        width: 24px;
    }

    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid #57534E;
        margin-right: 6px;
    }

    QComboBox QAbstractItemView {
        background-color: #FFFFFF;
        border: 1px solid #E7E5E4;
        border-radius: 6px;
        color: #1C1917;
        selection-background-color: #EEF2FF;
        selection-color: #3730A3;
        outline: none;
        padding: 4px;
    }

    /* ===== 表格（保留兼容） ===== */
    QTableWidget {
        background-color: #FFFFFF;
        border: 1px solid #E7E5E4;
        border-radius: 8px;
        gridline-color: #E7E5E4;
        selection-background-color: #EEF2FF;
        selection-color: #3730A3;
        outline: none;
    }

    QTableWidget::item {
        padding: 6px 10px;
        border-bottom: 1px solid #E7E5E4;
    }

    QTableWidget::item:selected {
        background-color: #EEF2FF;
        color: #3730A3;
    }

    QTableWidget::item:hover {
        background-color: #F5F5F4;
    }

    QHeaderView::section {
        background-color: #F5F5F4;
        border: none;
        border-bottom: 1px solid #E7E5E4;
        border-right: 1px solid #E7E5E4;
        padding: 8px 10px;
        color: #57534E;
        font-weight: 600;
        font-size: 12px;
    }

    /* ===== 分组框 ===== */
    QGroupBox {
        font-weight: 600;
        border: 1px solid #E7E5E4;
        border-radius: 8px;
        margin-top: 12px;
        padding: 20px 12px 12px 12px;
        background-color: #FFFFFF;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 8px;
        color: #4F46E5;
    }

    /* ===== 进度条 ===== */
    QProgressBar {
        border: none;
        border-radius: 6px;
        text-align: center;
        background-color: #E7E5E4;
        color: #1C1917;
        height: 12px;
        font-size: 11px;
    }

    QProgressBar::chunk {
        background-color: #4F46E5;
        border-radius: 6px;
    }

    /* ===== 列表 ===== */
    QListWidget {
        background-color: #FFFFFF;
        border: 1px solid #E7E5E4;
        border-radius: 8px;
        color: #1C1917;
        outline: none;
    }

    QListWidget::item {
        padding: 6px 10px;
        border-radius: 4px;
        margin: 2px 4px;
    }

    QListWidget::item:selected {
        background-color: #EEF2FF;
        color: #3730A3;
    }

    QListWidget::item:hover {
        background-color: #F5F5F4;
    }

    /* ===== 文本编辑 ===== */
    QTextEdit {
        background-color: #FFFFFF;
        border: 1px solid #E7E5E4;
        border-radius: 8px;
        color: #1C1917;
        padding: 8px;
    }

    QTextEdit:focus {
        border-color: #4F46E5;
    }

    /* ===== 分割器 ===== */
    QSplitter::handle {
        background-color: #E7E5E4;
        width: 1px;
    }

    QSplitter::handle:hover {
        background-color: #4F46E5;
    }

    /* ===== 状态栏 ===== */
    QStatusBar {
        background-color: #F5F5F4;
        border-top: 1px solid #E7E5E4;
        color: #57534E;
        padding: 4px 12px;
    }

    QStatusBar QLabel {
        color: #57534E;
        padding: 2px 8px;
    }

    /* ===== 单选/复选 ===== */
    QRadioButton, QCheckBox {
        spacing: 8px;
        color: #1C1917;
    }

    QRadioButton::indicator, QCheckBox::indicator {
        width: 16px;
        height: 16px;
    }

    /* ===== 滚动条 ===== */
    QScrollBar:vertical {
        background-color: #FAFAF9;
        width: 10px;
        border-radius: 5px;
        border: 2px solid #FAFAF9;
    }

    QScrollBar::handle:vertical {
        background-color: #D6D3D1;
        border-radius: 5px;
        min-height: 30px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #A8A29E;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    QScrollBar:horizontal {
        background-color: #FAFAF9;
        height: 10px;
        border-radius: 5px;
        border: 2px solid #FAFAF9;
    }

    QScrollBar::handle:horizontal {
        background-color: #D6D3D1;
        border-radius: 5px;
        min-width: 30px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: #A8A29E;
    }

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }

    /* ===== 标签页 ===== */
    QTabWidget::pane {
        border: 1px solid #E7E5E4;
        border-radius: 8px;
        background-color: #FFFFFF;
    }

    QTabBar::tab {
        background-color: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        padding: 10px 12px;
        margin-right: 4px;
        color: #A8A29E;
        font-size: 12px;
        font-weight: 500;
    }

    QTabBar::tab:selected {
        color: #1C1917;
        font-weight: 600;
        border-bottom: 2px solid #4F46E5;
    }

    QTabBar::tab:hover {
        color: #57534E;
    }

    /* ===== 工具提示 ===== */
    QToolTip {
        background-color: #FFFFFF;
        color: #1C1917;
        border: 1px solid #E7E5E4;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }

    /* ===== 菜单 ===== */
    QMenu {
        background-color: #FFFFFF;
        border: 1px solid #E7E5E4;
        border-radius: 8px;
        padding: 4px;
    }

    QMenu::item {
        padding: 8px 24px;
        border-radius: 4px;
        color: #1C1917;
    }

    QMenu::item:selected {
        background-color: #F5F5F4;
    }

    QMenu::separator {
        height: 1px;
        background-color: #E7E5E4;
        margin: 4px 8px;
    }

    /* ===== 文本浏览器 ===== */
    QTextBrowser {
        background-color: #FFFFFF;
        border: 1px solid #E7E5E4;
        border-radius: 8px;
        color: #1C1917;
        padding: 12px;
    }
    """


if __name__ == "__main__":
    # ProcessPoolExecutor 在 Windows 打包后用 spawn 模式启动子进程：
    # 子进程会重新执行 frozen 入口脚本。freeze_support 必须是 __main__ 第一行，
    # 否则子进程会再次走到 main() → 创建第二个 QApplication → 崩溃/卡死。
    import multiprocessing
    multiprocessing.freeze_support()
    main()
