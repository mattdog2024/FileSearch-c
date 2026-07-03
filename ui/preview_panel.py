"""预览面板 - 显示文件详情和内容预览"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QGroupBox, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QTextCursor, QTextCharFormat

from core.text_utils import highlight_text, format_file_size
import time


class PreviewPanel(QWidget):
    """文件预览面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 文件信息区
        info_group = QGroupBox("文件信息")
        info_layout = QVBoxLayout(info_group)

        self.lbl_filename = QLabel("文件名: -")
        self.lbl_filename.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.lbl_filename.setWordWrap(True)
        info_layout.addWidget(self.lbl_filename)

        self.lbl_path = QLabel("路径: -")
        self.lbl_path.setWordWrap(True)
        self.lbl_path.setStyleSheet("color: #666;")
        info_layout.addWidget(self.lbl_path)

        detail_layout = QHBoxLayout()
        self.lbl_size = QLabel("大小: -")
        self.lbl_time = QLabel("修改时间: -")
        self.lbl_status = QLabel("状态: -")
        detail_layout.addWidget(self.lbl_size)
        detail_layout.addWidget(self.lbl_time)
        detail_layout.addWidget(self.lbl_status)
        detail_layout.addStretch()
        info_layout.addLayout(detail_layout)

        layout.addWidget(info_group)

        # 内容预览区
        content_group = QGroupBox("内容预览")
        content_layout = QVBoxLayout(content_group)

        self.txt_preview = QTextEdit()
        self.txt_preview.setReadOnly(True)
        self.txt_preview.setFont(QFont("Microsoft YaHei", 9))
        self.txt_preview.setLineWrapMode(QTextEdit.WidgetWidth)
        content_layout.addWidget(self.txt_preview)

        layout.addWidget(content_group, stretch=1)

        # 初始提示
        self._show_placeholder()

    def _show_placeholder(self):
        self.lbl_filename.setText("文件名: 请选择一个文件")
        self.lbl_path.setText("路径: -")
        self.lbl_size.setText("大小: -")
        self.lbl_time.setText("修改时间: -")
        self.lbl_status.setText("状态: -")
        self.txt_preview.setPlainText("在左侧选择一个文件以预览内容")

    def show_file(self, search_result, root_path="", keywords=None):
        """显示文件信息和内容预览"""
        if search_result is None:
            self._show_placeholder()
            return

        r = search_result

        # 文件信息
        self.lbl_filename.setText(f"📄 {r.filename}")

        if root_path:
            import os
            full_path = os.path.join(root_path, r.relative_path)
            self.lbl_path.setText(f"📁 {full_path}")
        else:
            self.lbl_path.setText(f"📁 {r.relative_path}")

        self.lbl_size.setText(f"📏 {r.file_size_str}")
        self.lbl_time.setText(f"🕐 {r.modified_time_str}")

        if r.is_available:
            self.lbl_status.setText("✅ 可用")
            self.lbl_status.setStyleSheet("color: green;")
        else:
            self.lbl_status.setText("⚠️ 离线（文件所在硬盘未连接）")
            self.lbl_status.setStyleSheet("color: orange;")

        # 内容预览
        content = r.content or ""
        if not content:
            self.txt_preview.setPlainText("（此文件未提取到文本内容）")
            return

        if keywords:
            self._show_highlighted_content(content, keywords)
        else:
            # 显示前2000字符
            preview = content[:2000]
            if len(content) > 2000:
                preview += "\n\n... (内容过长，仅显示前2000字符)"
            self.txt_preview.setPlainText(preview)

    def _show_highlighted_content(self, content, keywords):
        """显示带高亮的内容"""
        self.txt_preview.clear()

        snippets = highlight_text(content, keywords, context_chars=100)

        cursor = self.txt_preview.textCursor()

        for i, (snippet, matches) in enumerate(snippets):
            if i > 0:
                cursor.insertText("\n\n" + "─" * 50 + "\n\n")

            # 插入片段文本
            if not matches:
                cursor.insertText(snippet)
            else:
                # 带高亮插入
                pos = 0
                for start, end in matches:
                    # 高亮前的普通文本
                    if start > pos:
                        cursor.insertText(snippet[pos:start])
                    # 高亮文本
                    fmt = QTextCharFormat()
                    fmt.setBackground(QColor("#FFEB3B"))
                    fmt.setForeground(QColor("#000000"))
                    fmt.setFontWeight(QFont.Bold)

                    saved_pos = cursor.position()
                    cursor.insertText(snippet[start:end])
                    cursor.setPosition(saved_pos)
                    cursor.setPosition(saved_pos + (end - start), QTextCursor.KeepAnchor)
                    cursor.mergeCharFormat(fmt)
                    cursor.clearSelection()
                    pos = end

                # 剩余文本
                if pos < len(snippet):
                    cursor.insertText(snippet[pos:])

        cursor.movePosition(QTextCursor.Start)
        self.txt_preview.setTextCursor(cursor)

    def clear(self):
        """清空预览"""
        self._show_placeholder()
