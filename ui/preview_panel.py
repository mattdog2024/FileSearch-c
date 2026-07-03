"""预览面板 - 文件信息与内容预览
现代化深色主题设计
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from core.text_utils import format_file_size


class PreviewPanel(QWidget):
    """文件预览面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- 文件信息卡片 ----
        self.info_card = QWidget()
        self.info_card.setObjectName("infoCard")
        self.info_card.setStyleSheet("""
            QWidget#infoCard {
                background-color: #181825;
                border-radius: 10px;
                border: 1px solid #313244;
            }
        """)
        info_layout = QVBoxLayout(self.info_card)
        info_layout.setContentsMargins(16, 14, 16, 14)
        info_layout.setSpacing(8)

        # 文件名标题
        self.lbl_filename = QLabel("选择一个文件查看详情")
        self.lbl_filename.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        self.lbl_filename.setStyleSheet("color: #cdd6f4;")
        self.lbl_filename.setWordWrap(True)
        info_layout.addWidget(self.lbl_filename)

        # 分隔线
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet("color: #313244;")
        info_layout.addWidget(sep1)

        # 文件属性网格
        attrs_layout = QHBoxLayout()
        attrs_layout.setSpacing(16)

        # 左侧属性
        left_attrs = QVBoxLayout()
        left_attrs.setSpacing(6)

        self.lbl_type = self._make_attr_label("类型", "—")
        self.lbl_size = self._make_attr_label("大小", "—")
        left_attrs.addWidget(self.lbl_type)
        left_attrs.addWidget(self.lbl_size)
        attrs_layout.addLayout(left_attrs)

        # 右侧属性
        right_attrs = QVBoxLayout()
        right_attrs.setSpacing(6)

        self.lbl_time = self._make_attr_label("修改时间", "—")
        self.lbl_source = self._make_attr_label("来源索引", "—")
        right_attrs.addWidget(self.lbl_time)
        right_attrs.addWidget(self.lbl_source)
        attrs_layout.addLayout(right_attrs)

        info_layout.addLayout(attrs_layout)

        # 文件路径
        self.lbl_path = QLabel("")
        self.lbl_path.setStyleSheet("color: #585b70; font-size: 11px;")
        self.lbl_path.setWordWrap(True)
        info_layout.addWidget(self.lbl_path)

        layout.addWidget(self.info_card)

        # ---- 内容预览区 ----
        preview_header = QWidget()
        preview_header.setStyleSheet("background-color: #1e1e2e;")
        ph_layout = QHBoxLayout(preview_header)
        ph_layout.setContentsMargins(4, 8, 4, 4)

        lbl_preview_title = QLabel("📄 内容预览")
        lbl_preview_title.setStyleSheet("color: #89b4fa; font-size: 12px; font-weight: 600;")
        ph_layout.addWidget(lbl_preview_title)
        ph_layout.addStretch()

        layout.addWidget(preview_header)

        # 预览文本框
        self.txt_preview = QTextEdit()
        self.txt_preview.setReadOnly(True)
        self.txt_preview.setFont(QFont("Consolas", 10))
        self.txt_preview.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
                color: #bac2de;
                padding: 12px;
                selection-background-color: #45475a;
                selection-color: #cdd6f4;
            }
        """)
        layout.addWidget(self.txt_preview, stretch=1)

        # ---- 关键词匹配片段区 ----
        self.snippet_header = QWidget()
        self.snippet_header.setStyleSheet("background-color: #1e1e2e;")
        sh_layout = QHBoxLayout(self.snippet_header)
        sh_layout.setContentsMargins(4, 8, 4, 4)

        lbl_snippet_title = QLabel("🔍 匹配片段")
        lbl_snippet_title.setStyleSheet("color: #f9e2af; font-size: 12px; font-weight: 600;")
        sh_layout.addWidget(lbl_snippet_title)
        sh_layout.addStretch()

        self.snippet_count_label = QLabel("")
        self.snippet_count_label.setStyleSheet("color: #585b70; font-size: 11px;")
        sh_layout.addWidget(self.snippet_count_label)

        layout.addWidget(self.snippet_header)

        self.txt_snippets = QTextEdit()
        self.txt_snippets.setReadOnly(True)
        self.txt_snippets.setFont(QFont("Microsoft YaHei", 10))
        self.txt_snippets.setStyleSheet("""
            QTextEdit {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 8px;
                color: #bac2de;
                padding: 10px;
                selection-background-color: #45475a;
                selection-color: #cdd6f4;
            }
        """)
        self.txt_snippets.setMaximumHeight(160)
        layout.addWidget(self.txt_snippets)

        self.snippet_header.setVisible(False)
        self.txt_snippets.setVisible(False)

        # 初始状态
        self.clear()

    def _make_attr_label(self, key, value):
        """创建属性标签"""
        lbl = QLabel(
            f'<span style="color:#585b70; font-size:11px;">{key}:</span> '
            f'<span style="color:#a6adc8; font-size:11px;">{value}</span>'
        )
        lbl.setTextFormat(Qt.RichText)
        return lbl

    def _update_attr_label(self, label, key, value):
        """更新属性标签"""
        label.setText(
            f'<span style="color:#585b70; font-size:11px;">{key}:</span> '
            f'<span style="color:#a6adc8; font-size:11px;">{value}</span>'
        )

    def show_file(self, result, keywords=None):
        """显示文件信息和内容预览

        result: SearchResult 对象（自带 root_path、db_path）
        keywords: 搜索关键词列表
        """
        # 文件名
        self.lbl_filename.setText(result.filename)

        # 属性
        ext_display = result.extension.upper().replace(".", "") if result.extension else "未知"
        self._update_attr_label(self.lbl_type, "类型", ext_display)
        self._update_attr_label(self.lbl_size, "大小", result.file_size_str)
        self._update_attr_label(self.lbl_time, "修改时间", result.modified_time_str)

        # 来源索引
        source = "—"
        if hasattr(result, 'db_path') and result.db_path:
            import os
            source = os.path.basename(result.db_path)
        self._update_attr_label(self.lbl_source, "来源索引", source)

        # 路径
        full_path = result.full_path
        self.lbl_path.setText(f"📂 {full_path}")

        # 可用性标记
        if result.is_available:
            self.lbl_path.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        else:
            self.lbl_path.setStyleSheet("color: #f38ba8; font-size: 11px;")

        # 内容预览
        content = result.content or ""
        if content:
            # 截取前 2000 字符显示
            preview_text = content[:2000]
            if len(content) > 2000:
                preview_text += "\n\n... (共 {} 字符，仅显示前 2000)".format(len(content))
            self.txt_preview.setPlainText(preview_text)
            self.txt_preview.setStyleSheet("""
                QTextEdit {
                    background-color: #1e1e2e;
                    border: 1px solid #313244;
                    border-radius: 8px;
                    color: #bac2de;
                    padding: 12px;
                    selection-background-color: #45475a;
                    selection-color: #cdd6f4;
                }
            """)
        else:
            self.txt_preview.setPlainText("(无内容预览)")
            self.txt_preview.setStyleSheet("""
                QTextEdit {
                    background-color: #1e1e2e;
                    border: 1px solid #313244;
                    border-radius: 8px;
                    color: #585b70;
                    padding: 12px;
                }
            """)

        # 关键词匹配片段
        if keywords and content:
            snippets = result.get_snippets(keywords)
            if snippets and snippets[0][1]:  # 有匹配
                self._show_snippets(snippets)
            else:
                self.snippet_header.setVisible(False)
                self.txt_snippets.setVisible(False)
        else:
            self.snippet_header.setVisible(False)
            self.txt_snippets.setVisible(False)

    def _show_snippets(self, snippets):
        """显示关键词匹配片段（HTML 高亮）"""
        self.snippet_header.setVisible(True)
        self.txt_snippets.setVisible(True)
        self.snippet_count_label.setText(f"{len(snippets)} 处匹配")

        html_parts = []
        for snippet, matches in snippets:
            # 转义 HTML
            escaped = snippet.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            # 高亮匹配（从后往前替换避免偏移）
            for start, end in reversed(matches):
                before = escaped[:start]
                matched = escaped[start:end]
                after = escaped[end:]
                escaped = (
                    f'{before}<span style="background-color:#f9e2af; color:#1e1e2e; '
                    f'border-radius:3px; padding:1px 3px; font-weight:bold;">{matched}</span>{after}'
                )

            html_parts.append(
                f'<div style="margin-bottom:8px; padding:6px 8px; '
                f'background-color:#313244; border-radius:6px; '
                f'font-size:12px; line-height:1.5;">'
                f'{escaped}</div>'
            )

        self.txt_snippets.setHtml("".join(html_parts))

    def clear(self):
        """清空预览"""
        self.lbl_filename.setText("选择一个文件查看详情")
        self._update_attr_label(self.lbl_type, "类型", "—")
        self._update_attr_label(self.lbl_size, "大小", "—")
        self._update_attr_label(self.lbl_time, "修改时间", "—")
        self._update_attr_label(self.lbl_source, "来源索引", "—")
        self.lbl_path.setText("")
        self.txt_preview.setPlainText("")
        self.txt_preview.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
                color: #585b70;
                padding: 12px;
            }
        """)
        self.snippet_header.setVisible(False)
        self.txt_snippets.setVisible(False)
