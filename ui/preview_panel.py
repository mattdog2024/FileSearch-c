"""预览面板 - 明亮暖白主题
PreviewHeader / PreviewBody / PreviewFooter 三段式布局
"""
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QStackedWidget, QTextBrowser, QPushButton, QSizePolicy,
    QTabWidget, QGridLayout
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QColor, QDesktopServices

from core.text_utils import format_file_size


class PreviewPanel(QWidget):
    """文件预览面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_result = None
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("QWidget { background-color: #FFFFFF; }")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== PreviewHeader =====
        self.header = self._build_header()
        main_layout.addWidget(self.header)

        # ===== PreviewBody =====
        self.body = self._build_body()
        main_layout.addWidget(self.body, stretch=1)

        # ===== PreviewFooter =====
        self.footer = self._build_footer()
        main_layout.addWidget(self.footer)

        # 初始状态
        self.clear()

    def _build_header(self):
        """构建预览头部"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E7E5E4;
            }
        """)

        layout = QVBoxLayout(header)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(12)

        # 面包屑
        self.lbl_breadcrumb = QLabel("")
        self.lbl_breadcrumb.setTextFormat(Qt.RichText)
        self.lbl_breadcrumb.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-family: "Consolas", "JetBrains Mono", monospace;
                color: #A8A29E;
                background: transparent;
            }
        """)
        layout.addWidget(self.lbl_breadcrumb)

        # 标题行
        title_row = QHBoxLayout()
        title_row.setSpacing(12)

        self.lbl_title = QLabel("选择一个文件查看详情")
        self.lbl_title.setStyleSheet("""
            QLabel {
                font-size: 22px;
                font-weight: 700;
                color: #1C1917;
                background: transparent;
            }
        """)
        self.lbl_title.setWordWrap(True)
        title_row.addWidget(self.lbl_title, stretch=1)

        # 操作按钮组
        btn_group = QVBoxLayout()
        btn_group.setSpacing(6)

        self.btn_open = QPushButton("打开文件")
        self.btn_open.setObjectName("primaryBtn")
        self.btn_open.setFixedHeight(30)
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.clicked.connect(self._open_file)
        self.btn_open.setEnabled(False)
        btn_group.addWidget(self.btn_open)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.btn_locate = QPushButton("定位")
        self.btn_locate.setFixedHeight(30)
        self.btn_locate.setCursor(Qt.PointingHandCursor)
        self.btn_locate.clicked.connect(self._locate_file)
        self.btn_locate.setEnabled(False)
        btn_row.addWidget(self.btn_locate)

        self.btn_copy_path = QPushButton("复制路径")
        self.btn_copy_path.setFixedHeight(30)
        self.btn_copy_path.setCursor(Qt.PointingHandCursor)
        self.btn_copy_path.clicked.connect(self._copy_path)
        self.btn_copy_path.setEnabled(False)
        btn_row.addWidget(self.btn_copy_path)

        btn_group.addLayout(btn_row)
        title_row.addLayout(btn_group)

        layout.addLayout(title_row)

        # 元信息区（4列）
        meta_grid = QHBoxLayout()
        meta_grid.setSpacing(28)

        self.meta_type = self._build_meta_cell("类型", "—")
        self.meta_size = self._build_meta_cell("大小", "—")
        self.meta_time = self._build_meta_cell("修改时间", "—")
        self.meta_path = self._build_meta_cell("路径", "—", mono=True)

        meta_grid.addWidget(self.meta_type["widget"])
        meta_grid.addWidget(self.meta_size["widget"])
        meta_grid.addWidget(self.meta_time["widget"])
        meta_grid.addWidget(self.meta_path["widget"])

        layout.addLayout(meta_grid)

        return header

    def _build_meta_cell(self, key, value, mono=False):
        """构建元信息单元格"""
        widget = QWidget()
        widget.setStyleSheet("QWidget { background: transparent; }")
        v_layout = QVBoxLayout(widget)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(2)

        lbl_key = QLabel(key.upper())
        lbl_key.setStyleSheet("""
            QLabel {
                font-size: 10px;
                font-weight: 600;
                color: #A8A29E;
                background: transparent;
            }
        """)
        v_layout.addWidget(lbl_key)

        font_family = '"Consolas", "JetBrains Mono", monospace' if mono else '"Microsoft YaHei UI", sans-serif'
        font_size = "12px" if mono else "13px"
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(f"""
            QLabel {{
                font-size: {font_size};
                font-weight: 500;
                color: #1C1917;
                font-family: {font_family};
                background: transparent;
            }}
        """)
        lbl_value.setWordWrap(True)
        v_layout.addWidget(lbl_value)

        return {"widget": widget, "key": lbl_key, "value": lbl_value}

    def _build_body(self):
        """构建预览主体"""
        body = QWidget()
        body.setStyleSheet("QWidget { background-color: #FFFFFF; }")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(24, 24, 24, 28)
        layout.setSpacing(0)

        # Tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #FFFFFF;
            }
            QTabBar::tab {
                background-color: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                padding: 10px 12px 12px;
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
        """)

        # 内容预览（富文本）
        self.txt_preview = QTextBrowser()
        self.txt_preview.setOpenExternalLinks(False)
        self.txt_preview.setStyleSheet("""
            QTextBrowser {
                background-color: #FFFFFF;
                border: none;
                color: #1C1917;
                font-size: 13.5px;
                line-height: 1.75;
                padding: 0;
            }
        """)
        self.tab_widget.addTab(self.txt_preview, "内容预览")

        # 匹配片段
        self.txt_snippets = QTextBrowser()
        self.txt_snippets.setStyleSheet("""
            QTextBrowser {
                background-color: #FFFFFF;
                border: none;
                color: #1C1917;
                font-size: 13px;
                line-height: 1.55;
                padding: 0;
            }
        """)
        self.tab_widget.addTab(self.txt_snippets, "匹配片段")

        layout.addWidget(self.tab_widget, stretch=1)

        return body

    def _build_footer(self):
        """构建预览底部"""
        footer = QFrame()
        footer.setStyleSheet("""
            QFrame {
                background-color: #F5F5F4;
                border-top: 1px solid #E7E5E4;
            }
        """)

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(24, 12, 24, 12)

        # 左侧：编码信息
        self.lbl_footer_info = QLabel("UTF-8")
        self.lbl_footer_info.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-family: "Consolas", "JetBrains Mono", monospace;
                color: #A8A29E;
                background: transparent;
            }
        """)
        layout.addWidget(self.lbl_footer_info)

        layout.addStretch()

        # 右侧：来源 tag
        source_container = QHBoxLayout()
        source_container.setSpacing(6)

        lbl_source_label = QLabel("来源：")
        lbl_source_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #A8A29E;
                background: transparent;
            }
        """)
        source_container.addWidget(lbl_source_label)

        # 绿点
        self.lbl_status_dot = QLabel("●")
        self.lbl_status_dot.setStyleSheet("""
            QLabel {
                font-size: 6px;
                color: #059669;
                background: transparent;
            }
        """)
        source_container.addWidget(self.lbl_status_dot)

        # 来源名
        self.lbl_source_tag = QLabel("—")
        self.lbl_source_tag.setStyleSheet("""
            QLabel {
                background-color: #FFFFFF;
                border: 1px solid #E7E5E4;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-family: "Consolas", "JetBrains Mono", monospace;
                color: #57534E;
            }
        """)
        source_container.addWidget(self.lbl_source_tag)

        layout.addLayout(source_container)

        return footer

    def show_file(self, result, keywords=None):
        """显示文件信息和内容预览"""
        self._current_result = result

        # 面包屑
        path_parts = result.relative_path.replace('\\', '/').split('/')
        breadcrumb_parts = [f'<span style="color:#A8A29E;">{p}</span>' for p in path_parts[:-1]]
        breadcrumb_parts.append(f'<span style="color:#57534E;font-weight:500;">{path_parts[-1]}</span>' if path_parts else '')
        self.lbl_breadcrumb.setText(' <span style="color:rgba(168,162,158,0.5);">/</span> '.join(breadcrumb_parts))

        # 标题
        self.lbl_title.setText(result.filename)

        # 元信息
        ext_display = result.extension.upper().replace(".", "") if result.extension else "未知"
        self.meta_type["value"].setText(ext_display)
        self.meta_size["value"].setText(result.file_size_str)
        self.meta_time["value"].setText(result.modified_time_str)
        self.meta_path["value"].setText(result.relative_path)

        # 按钮
        self.btn_open.setEnabled(True)
        self.btn_locate.setEnabled(True)
        self.btn_copy_path.setEnabled(True)

        # 内容预览
        content = result.content or ""
        if content:
            # 高亮关键词
            preview_html = content[:3000]
            preview_html = preview_html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            preview_html = preview_html.replace("\n", "<br>")

            if keywords:
                for kw in keywords:
                    kw_escaped = kw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    preview_html = preview_html.replace(
                        kw_escaped,
                        f'<span style="background:#FEF3C7;color:#78350F;padding:1px 3px;border-radius:3px;font-weight:500;">{kw_escaped}</span>'
                    )

            self.txt_preview.setHtml(
                f'<div style="max-width:720px;font-size:13.5px;line-height:1.75;color:#1C1917;">'
                f'{preview_html}'
                f'</div>'
            )
        else:
            self.txt_preview.setHtml(
                '<div style="color:#A8A29E;font-size:13px;padding:20px;">'
                '（无内容预览）</div>'
            )

        # 匹配片段
        if keywords and content:
            snippets = result.get_snippets(keywords)
            if snippets and snippets[0][1]:
                self._show_snippets(snippets, keywords)
                self.tab_widget.setTabText(1, f"匹配片段 ({len(snippets)})")
            else:
                self.txt_snippets.setHtml(
                    '<div style="color:#A8A29E;font-size:13px;padding:20px;">'
                    '（无匹配片段）</div>'
                )
                self.tab_widget.setTabText(1, "匹配片段")
        else:
            self.txt_snippets.setHtml(
                '<div style="color:#A8A29E;font-size:13px;padding:20px;">'
                '（无匹配片段）</div>'
            )
            self.tab_widget.setTabText(1, "匹配片段")

        # 默认显示内容预览
        self.tab_widget.setCurrentIndex(0)

        # Footer
        self.lbl_footer_info.setText(f"UTF-8  ·  {result.file_size_str}")
        source_name = "—"
        if hasattr(result, 'source_name') and result.source_name:
            source_name = result.source_name
        elif hasattr(result, 'db_path') and result.db_path:
            source_name = os.path.basename(result.db_path)
        self.lbl_source_tag.setText(source_name)

    def _show_snippets(self, snippets, keywords=None):
        """显示关键词匹配片段"""
        html_parts = []
        for snippet, matches in snippets:
            escaped = snippet.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            # 高亮匹配
            for start, end in reversed(matches):
                before = escaped[:start]
                matched = escaped[start:end]
                after = escaped[end:]
                escaped = (
                    f'{before}<span style="background:#FEF3C7;color:#78350F;'
                    f'padding:1px 3px;border-radius:3px;font-weight:500;'
                    f'box-shadow:0 0 0 2px #FEF3C7;">{matched}</span>{after}'
                )

            html_parts.append(
                f'<div style="margin-bottom:10px;padding:10px 12px;'
                f'background:#F5F5F4;border-radius:8px;'
                f'font-size:12px;line-height:1.55;color:#57534E;">'
                f'{escaped}</div>'
            )

        self.txt_snippets.setHtml("".join(html_parts))

    def _open_file(self):
        """打开文件"""
        if not self._current_result:
            return
        full_path = self._current_result.full_path
        if os.path.exists(full_path):
            import subprocess, sys
            if sys.platform == "win32":
                os.startfile(full_path)
            else:
                subprocess.Popen(["xdg-open", full_path])

    def _locate_file(self):
        """定位到文件所在文件夹"""
        if not self._current_result:
            return
        full_path = self._current_result.full_path
        folder = os.path.dirname(full_path)
        if os.path.exists(folder):
            import subprocess, sys
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", full_path])
            else:
                subprocess.Popen(["xdg-open", folder])

    def _copy_path(self):
        """复制路径到剪贴板"""
        if not self._current_result:
            return
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self._current_result.full_path)

    def clear(self):
        """清空预览"""
        self._current_result = None
        self.lbl_breadcrumb.setText("")
        self.lbl_title.setText("选择一个文件查看详情")
        self.meta_type["value"].setText("—")
        self.meta_size["value"].setText("—")
        self.meta_time["value"].setText("—")
        self.meta_path["value"].setText("—")
        self.btn_open.setEnabled(False)
        self.btn_locate.setEnabled(False)
        self.btn_copy_path.setEnabled(False)
        self.txt_preview.setHtml(
            '<div style="color:#A8A29E;font-size:13px;padding:40px;text-align:center;">'
            '选择一个文件以预览内容</div>'
        )
        self.txt_snippets.setHtml("")
        self.lbl_footer_info.setText("")
        self.lbl_source_tag.setText("—")
