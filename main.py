"""FileSearch - 文件全文搜索索引工具
入口文件
"""
import sys
import os

# ---- 中文编码修复（Windows 打包后关键）----
# 确保 Windows 下使用 UTF-8 编码
if sys.platform == "win32":
    # 设置环境变量，影响子进程和库的编码行为
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    # 修复 sys.stdout/stderr 编码（打包后无控制台时可能为 None）
    try:
        if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# PyInstaller 打包后的路径处理
if getattr(sys, 'frozen', False):
    # 打包后 __file__ 在临时目录，改用 exe 所在目录
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
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("FileSearch")

    # 设置样式
    app.setStyleSheet(_get_stylesheet())

    # 创建主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


def _get_stylesheet():
    """获取全局样式表"""
    return """
    QMainWindow {
        background-color: #f5f5f5;
    }

    QLineEdit {
        border: 2px solid #ddd;
        border-radius: 4px;
        padding: 6px 12px;
        background-color: white;
        selection-background-color: #2196F3;
    }

    QLineEdit:focus {
        border-color: #2196F3;
    }

    QPushButton {
        background-color: #e0e0e0;
        border: 1px solid #ccc;
        border-radius: 4px;
        padding: 6px 16px;
        min-height: 24px;
    }

    QPushButton:hover {
        background-color: #d0d0d0;
    }

    QPushButton:pressed {
        background-color: #c0c0c0;
    }

    QTableWidget {
        background-color: white;
        alternate-background-color: #f9f9f9;
        border: 1px solid #ddd;
        gridline-color: #eee;
        selection-background-color: #e3f2fd;
        selection-color: #000;
    }

    QTableWidget::item {
        padding: 4px 8px;
    }

    QHeaderView::section {
        background-color: #f0f0f0;
        border: 1px solid #ddd;
        padding: 6px;
        font-weight: bold;
    }

    QGroupBox {
        font-weight: bold;
        border: 1px solid #ddd;
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 16px;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }

    QProgressBar {
        border: 1px solid #ddd;
        border-radius: 4px;
        text-align: center;
        background-color: #f0f0f0;
    }

    QProgressBar::chunk {
        background-color: #4CAF50;
        border-radius: 3px;
    }

    QComboBox {
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 4px 8px;
        background-color: white;
    }

    QComboBox:hover {
        border-color: #2196F3;
    }

    QListWidget {
        border: 1px solid #ddd;
        border-radius: 4px;
        background-color: white;
    }

    QListWidget::item:selected {
        background-color: #e3f2fd;
        color: #000;
    }

    QTextEdit {
        border: 1px solid #ddd;
        border-radius: 4px;
        background-color: white;
    }

    QSplitter::handle {
        background-color: #ddd;
        width: 2px;
    }

    QStatusBar {
        background-color: #f0f0f0;
        border-top: 1px solid #ddd;
    }

    QTabWidget::pane {
        border: 1px solid #ddd;
    }

    QRadioButton, QCheckBox {
        spacing: 6px;
    }
    """


if __name__ == "__main__":
    main()
