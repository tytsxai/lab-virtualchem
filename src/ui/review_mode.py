"""
复习模式UI

提供错题复习的交互界面：
- 逐题复习
- 答案检查
- 进度跟踪
- 复习报告
"""

import logging
from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
)

logger = logging.getLogger(__name__)


class ReviewMode(QDialog):
    """复习模式对话框"""

    # 信号
    review_completed = pyqtSignal(dict)  # 复习完成信号，传递结果

    def __init__(self, student_id: str, mistake_ids: list, mistake_book=None, parent=None):
        """
        初始化复习模式

        Args:
            student_id: 学生ID
            mistake_ids: 要复习的错题ID列表
            mistake_book: 错题本实例
            parent: 父窗口
        """
        super().__init__(parent)

        self.student_id = student_id
        self.mistake_ids = mistake_ids

        # 导入错题本
        if mistake_book is None:
            from src.features import mistake_book as default_book

            self.mistake_book = default_book
        else:
            self.mistake_book = mistake_book

        self.mistakes = []
        self.current_index = 0
        self.correct_count = 0
        self.start_time = datetime.now()

        self.setup_ui()
        self.load_mistakes()
        self.show_current_mistake()

        logger.info(f"复习模式已启动: {len(mistake_ids)} 个错题")

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("错题复习")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # 顶部进度
        progress_layout = self.create_progress_bar()
        layout.addLayout(progress_layout)

        # 题目显示区
        question_group = self.create_question_area()
        layout.addWidget(question_group)

        # 答案区域
        answer_group = self.create_answer_area()
        layout.addWidget(answer_group)

        # 反馈区域
        self.feedback_group = self.create_feedback_area()
        self.feedback_group.hide()  # 初始隐藏
        layout.addWidget(self.feedback_group)

        # 底部按钮
        buttons = self.create_buttons()
        layout.addLayout(buttons)

    def create_progress_bar(self) -> QHBoxLayout:
        """创建进度条"""
        layout = QHBoxLayout()

        self.progress_label = QLabel("题目 1/0")
        self.progress_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.correct_label = QLabel("正确: 0 / 0")
        layout.addWidget(self.correct_label)

        return layout

    def create_question_area(self) -> QGroupBox:
        """创建题目区域"""
        group = QGroupBox("题目")
        layout = QVBoxLayout()

        # 实验信息
        self.exp_label = QLabel()
        self.exp_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(self.exp_label)

        # 错误类型
        self.type_label = QLabel()
        layout.addWidget(self.type_label)

        # 错误描述
        layout.addWidget(QLabel("错误描述:"))
        self.desc_text = QTextEdit()
        self.desc_text.setReadOnly(True)
        self.desc_text.setMaximumHeight(100)
        layout.addWidget(self.desc_text)

        # 你的答案
        layout.addWidget(QLabel("你当时的答案:"))
        self.student_answer_text = QTextEdit()
        self.student_answer_text.setReadOnly(True)
        self.student_answer_text.setMaximumHeight(80)
        layout.addWidget(self.student_answer_text)

        group.setLayout(layout)
        return group

    def create_answer_area(self) -> QGroupBox:
        """创建答案区域"""
        group = QGroupBox("现在你认为正确答案是什么？")
        layout = QVBoxLayout()

        # 答案输入
        self.answer_input = QTextEdit()
        self.answer_input.setPlaceholderText("请输入你现在的答案...")
        self.answer_input.setMaximumHeight(100)
        layout.addWidget(self.answer_input)

        # 或选择"我已掌握"
        self.mastered_radio = QRadioButton("我已完全掌握这个知识点")
        layout.addWidget(self.mastered_radio)

        group.setLayout(layout)
        return group

    def create_feedback_area(self) -> QGroupBox:
        """创建反馈区域"""
        group = QGroupBox("正确答案")
        layout = QVBoxLayout()

        self.correct_answer_text = QTextEdit()
        self.correct_answer_text.setReadOnly(True)
        layout.addWidget(self.correct_answer_text)

        # 判断结果
        self.result_label = QLabel()
        self.result_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(self.result_label)

        group.setLayout(layout)
        return group

    def create_buttons(self) -> QHBoxLayout:
        """创建按钮"""
        layout = QHBoxLayout()

        # 显示答案按钮
        self.show_answer_btn = QPushButton("查看正确答案")
        self.show_answer_btn.clicked.connect(self.on_show_answer)
        layout.addWidget(self.show_answer_btn)

        # 检查答案按钮
        self.check_answer_btn = QPushButton("检查答案")
        self.check_answer_btn.clicked.connect(self.on_check_answer)
        layout.addWidget(self.check_answer_btn)

        layout.addStretch()

        # 下一题按钮
        self.next_btn = QPushButton("下一题")
        self.next_btn.clicked.connect(self.on_next)
        self.next_btn.setEnabled(False)
        layout.addWidget(self.next_btn)

        # 完成按钮
        self.finish_btn = QPushButton("完成复习")
        self.finish_btn.clicked.connect(self.on_finish)
        self.finish_btn.setVisible(False)
        layout.addWidget(self.finish_btn)

        return layout

    def load_mistakes(self):
        """加载错题"""
        for mistake_id in self.mistake_ids:
            mistakes = self.mistake_book.get_student_mistakes(self.student_id)
            for m in mistakes:
                if m.mistake_id == mistake_id:
                    self.mistakes.append(m)
                    break

        # 更新进度条
        self.progress_bar.setMaximum(len(self.mistakes))
        self.update_progress()

    def show_current_mistake(self):
        """显示当前错题"""
        if self.current_index >= len(self.mistakes):
            return

        mistake = self.mistakes[self.current_index]

        # 更新题目信息
        self.exp_label.setText(f"实验: {mistake.experiment_name}")

        type_map = {
            "operation": "操作错误",
            "calculation": "计算错误",
            "concept": "概念错误",
            "safety": "安全错误",
            "other": "其他错误",
        }
        self.type_label.setText(f"类型: {type_map.get(mistake.mistake_type, mistake.mistake_type)}")

        self.desc_text.setPlainText(mistake.mistake_description)
        self.student_answer_text.setPlainText(mistake.student_answer)

        # 清空输入
        self.answer_input.clear()
        self.mastered_radio.setChecked(False)

        # 隐藏反馈
        self.feedback_group.hide()

        # 重置按钮状态
        self.show_answer_btn.setEnabled(True)
        self.check_answer_btn.setEnabled(True)
        self.next_btn.setEnabled(False)

        # 更新进度
        self.update_progress()

    def update_progress(self):
        """更新进度"""
        total = len(self.mistakes)
        current = self.current_index + 1

        self.progress_label.setText(f"题目 {current}/{total}")
        self.progress_bar.setValue(current)
        self.correct_label.setText(f"正确: {self.correct_count} / {total}")

        # 检查是否是最后一题
        if self.current_index >= total - 1:
            self.next_btn.setVisible(False)
            self.finish_btn.setVisible(True)
        else:
            self.next_btn.setVisible(True)
            self.finish_btn.setVisible(False)

    def on_show_answer(self):
        """显示答案"""
        if self.current_index >= len(self.mistakes):
            return

        mistake = self.mistakes[self.current_index]

        # 显示正确答案
        self.correct_answer_text.setPlainText(mistake.correct_answer)
        self.feedback_group.show()
        self.result_label.setText("")

        # 标记为已复习
        self.mistake_book.mark_as_reviewed(
            mistake.mistake_id, self.student_id, mastered=self.mastered_radio.isChecked()
        )

        # 启用下一题
        self.next_btn.setEnabled(True)
        self.show_answer_btn.setEnabled(False)
        self.check_answer_btn.setEnabled(False)

    def on_check_answer(self):
        """检查答案"""
        if self.current_index >= len(self.mistakes):
            return

        mistake = self.mistakes[self.current_index]
        student_answer = self.answer_input.toPlainText().strip()

        # 显示正确答案
        self.correct_answer_text.setPlainText(mistake.correct_answer)
        self.feedback_group.show()

        # 简单的答案比对（可以改进为更智能的比对）
        is_correct = False

        if self.mastered_radio.isChecked():
            is_correct = True
            self.result_label.setText("✓ 很好！你已经掌握了这个知识点！")
            self.result_label.setStyleSheet("color: green;")
        elif student_answer:
            # 简单的文本相似度检查
            if student_answer.lower() == mistake.correct_answer.lower():
                is_correct = True
                self.result_label.setText("✓ 完全正确！")
                self.result_label.setStyleSheet("color: green;")
            elif any(word in student_answer.lower() for word in mistake.correct_answer.lower().split()):
                is_correct = True
                self.result_label.setText("✓ 基本正确！")
                self.result_label.setStyleSheet("color: blue;")
            else:
                self.result_label.setText("✗ 还需要继续复习")
                self.result_label.setStyleSheet("color: red;")
        else:
            self.result_label.setText("请输入答案或选择'我已掌握'")
            self.result_label.setStyleSheet("color: orange;")
            return

        # 更新统计
        if is_correct:
            self.correct_count += 1

        # 标记为已复习
        self.mistake_book.mark_as_reviewed(mistake.mistake_id, self.student_id, mastered=is_correct)

        # 启用下一题
        self.next_btn.setEnabled(True)
        self.show_answer_btn.setEnabled(False)
        self.check_answer_btn.setEnabled(False)

        self.update_progress()

    def on_next(self):
        """下一题"""
        self.current_index += 1

        if self.current_index < len(self.mistakes):
            self.show_current_mistake()
        else:
            self.on_finish()

    def on_finish(self):
        """完成复习"""
        # 计算复习时间
        duration = (datetime.now() - self.start_time).total_seconds()

        # 创建复习记录
        record = self.mistake_book.create_review_session(self.student_id, self.mistake_ids)

        # 更新记录
        self.mistake_book.update_review_session(
            record.record_id,
            self.student_id,
            duration=int(duration),
            correct_count=self.correct_count,
            total_count=len(self.mistakes),
        )

        # 显示结果
        accuracy = (self.correct_count / len(self.mistakes) * 100) if self.mistakes else 0

        result_msg = (
            "复习完成！\n\n"
            f"总题数: {len(self.mistakes)}\n"
            f"正确数: {self.correct_count}\n"
            f"准确率: {accuracy:.1f}%\n"
            f"用时: {int(duration // 60)}分{int(duration % 60)}秒\n\n"
        )

        if accuracy >= 90:
            result_msg += "表现优秀！继续保持！ 🌟"
        elif accuracy >= 70:
            result_msg += "表现良好！再接再厉！ 👍"
        elif accuracy >= 50:
            result_msg += "还需努力！加油！ 💪"
        else:
            result_msg += "需要加强复习！ 📚"

        QMessageBox.information(self, "复习完成", result_msg)

        # 发送完成信号
        self.review_completed.emit(
            {
                "total": len(self.mistakes),
                "correct": self.correct_count,
                "accuracy": accuracy,
                "duration": duration,
            }
        )

        self.accept()


class QuickReviewDialog(QDialog):
    """快速复习对话框"""

    def __init__(self, student_id: str, mistake_analyzer=None, parent=None):
        """
        初始化快速复习

        Args:
            student_id: 学生ID
            mistake_analyzer: 错题分析器
            parent: 父窗口
        """
        super().__init__(parent)

        self.student_id = student_id

        if mistake_analyzer is None:
            from src.features import mistake_analyzer as default_analyzer

            self.mistake_analyzer = default_analyzer
        else:
            self.mistake_analyzer = mistake_analyzer

        self.setup_ui()
        self.load_suggestions()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("今日复习建议")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)

        # 标题
        title = QLabel("📚 今日复习建议")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 建议内容
        self.suggestion_text = QTextEdit()
        self.suggestion_text.setReadOnly(True)
        layout.addWidget(self.suggestion_text)

        # 按钮
        buttons = QHBoxLayout()

        start_btn = QPushButton("开始复习")
        start_btn.clicked.connect(self.accept)
        buttons.addWidget(start_btn)

        skip_btn = QPushButton("稍后复习")
        skip_btn.clicked.connect(self.reject)
        buttons.addWidget(skip_btn)

        layout.addLayout(buttons)

    def load_suggestions(self):
        """加载建议"""
        from src.features import mistake_book

        suggestions = mistake_book.get_review_suggestions(self.student_id, limit=5)

        if not suggestions:
            self.suggestion_text.setHtml("<h3>恭喜！</h3><p>暂无需要复习的错题。</p><p>继续保持，做更多练习！</p>")
        else:
            html = "<h3>建议复习以下错题：</h3><ol>"

            for mistake in suggestions:
                html += "<li>" f"<b>{mistake.experiment_name}</b> - " f"{mistake.mistake_description[:50]}..." "</li>"

            html += "</ol>"
            html += f"<p>共 <b>{len(suggestions)}</b> 个错题待复习</p>"

            self.suggestion_text.setHtml(html)
