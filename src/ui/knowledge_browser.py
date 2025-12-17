"""
知识浏览器
提供知识库浏览功能
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QTextEdit, QVBoxLayout

from ..utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeBrowser(QDialog):
    """知识浏览器"""

    def __init__(self, knowledge_dir: str, i18n_dir: str, parent=None):
        """初始化知识浏览器

        Args:
            knowledge_dir: 知识库目录
            i18n_dir: 国际化目录
            parent: 父控件
        """
        super().__init__(parent)
        self.knowledge_dir = Path(knowledge_dir)
        self.i18n_dir = Path(i18n_dir)

        self.setWindowTitle("知识库浏览器")
        self.setModal(True)
        self.resize(800, 600)

        self.init_ui()
        self.load_knowledge()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 文本显示区域
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        # 按钮区域
        button_layout = QHBoxLayout()

        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def load_knowledge(self):
        """加载知识内容"""
        try:
            content = []

            # 遍历知识库目录
            if self.knowledge_dir.exists():
                for file_path in self.knowledge_dir.glob("*.json"):
                    try:
                        import json

                        with open(file_path, encoding="utf-8") as f:
                            data = json.load(f)
                            content.append(f"## {file_path.stem}")
                            content.append(str(data))
                            content.append("")
                    except Exception as e:
                        logger.warning(f"加载知识文件失败: {file_path}, 错误: {e}")

            if not content:
                content = ["暂无知识内容"]

            self.text_edit.setPlainText("\n".join(content))
            logger.info("知识内容加载完成")

        except Exception as e:
            logger.error(f"加载知识内容失败: {e}")
            self.text_edit.setPlainText(f"加载失败: {e}")
