"""
错题查看器UI

提供错题浏览和管理的图形界面：
- 错题列表显示
- 分类筛选
- 详情查看
- 标记复习状态
"""

import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class MistakeViewer(QDialog):
    """错题查看器对话框"""

    # 信号
    start_review = Signal(list)  # 开始复习信号，传递错题ID列表

    def __init__(self, student_id: str, mistake_book=None, parent=None):
        """
        初始化错题查看器

        Args:
            student_id: 学生ID
            mistake_book: 错题本实例
            parent: 父窗口
        """
        super().__init__(parent)

        self.student_id = student_id

        # 导入错题本
        if mistake_book is None:
            from src.features import mistake_book as default_book

            self.mistake_book = default_book
        else:
            self.mistake_book = mistake_book

        self.current_mistakes = []
        self.selected_mistake = None

        self.setup_ui()
        self.load_mistakes()

        logger.info(f"错题查看器已打开: 学生ID={student_id}")

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("我的错题本")
        self.setMinimumSize(1000, 700)

        layout = QVBoxLayout(self)

        # 顶部工具栏
        toolbar = self.create_toolbar()
        layout.addLayout(toolbar)

        # 主分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：错题列表
        list_widget = self.create_mistake_list()
        splitter.addWidget(list_widget)

        # 右侧：详情面板
        detail_widget = self.create_detail_panel()
        splitter.addWidget(detail_widget)

        # 设置分割比例
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        # 底部按钮
        buttons = self.create_bottom_buttons()
        layout.addLayout(buttons)

    def create_toolbar(self) -> QHBoxLayout:
        """创建工具栏"""
        toolbar = QHBoxLayout()

        # 筛选器
        toolbar.addWidget(QLabel("筛选:"))

        # 错误类型筛选
        self.type_filter = QComboBox()
        self.type_filter.addItem("全部类型", "")
        self.type_filter.addItem("操作错误", "operation")
        self.type_filter.addItem("计算错误", "calculation")
        self.type_filter.addItem("概念错误", "concept")
        self.type_filter.addItem("安全错误", "safety")
        self.type_filter.addItem("其他", "other")
        self.type_filter.currentIndexChanged.connect(self.apply_filters)
        toolbar.addWidget(self.type_filter)

        # 复习状态筛选
        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态", None)
        self.status_filter.addItem("未复习", False)
        self.status_filter.addItem("已复习", True)
        self.status_filter.currentIndexChanged.connect(self.apply_filters)
        toolbar.addWidget(self.status_filter)

        toolbar.addStretch()

        # 统计标签
        self.stats_label = QLabel()
        toolbar.addWidget(self.stats_label)

        return toolbar

    def create_mistake_list(self) -> QWidget:
        """创建错题列表"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["日期", "实验", "类型", "描述", "状态", "掌握"]
        )

        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        # 选择模式
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)

        # 双击查看详情
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

        layout.addWidget(self.table)

        return widget

    def create_detail_panel(self) -> QWidget:
        """创建详情面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 基本信息组
        info_group = QGroupBox("错误信息")
        info_layout = QVBoxLayout()

        self.exp_label = QLabel()
        self.type_label = QLabel()
        self.date_label = QLabel()

        info_layout.addWidget(self.exp_label)
        info_layout.addWidget(self.type_label)
        info_layout.addWidget(self.date_label)
        info_group.setLayout(info_layout)

        layout.addWidget(info_group)

        # 错误描述
        desc_group = QGroupBox("错误描述")
        desc_layout = QVBoxLayout()

        self.desc_text = QTextEdit()
        self.desc_text.setReadOnly(True)
        self.desc_text.setMaximumHeight(100)
        desc_layout.addWidget(self.desc_text)

        desc_group.setLayout(desc_layout)
        layout.addWidget(desc_group)

        # 答案对比
        answer_group = QGroupBox("答案对比")
        answer_layout = QVBoxLayout()

        answer_layout.addWidget(QLabel("正确答案:"))
        self.correct_answer_text = QTextEdit()
        self.correct_answer_text.setReadOnly(True)
        self.correct_answer_text.setMaximumHeight(80)
        answer_layout.addWidget(self.correct_answer_text)

        answer_layout.addWidget(QLabel("你的答案:"))
        self.student_answer_text = QTextEdit()
        self.student_answer_text.setReadOnly(True)
        self.student_answer_text.setMaximumHeight(80)
        answer_layout.addWidget(self.student_answer_text)

        answer_group.setLayout(answer_layout)
        layout.addWidget(answer_group)

        # 复习状态
        status_group = QGroupBox("复习状态")
        status_layout = QVBoxLayout()

        self.reviewed_checkbox = QCheckBox("已复习")
        self.reviewed_checkbox.stateChanged.connect(self.on_reviewed_changed)
        status_layout.addWidget(self.reviewed_checkbox)

        self.mastered_checkbox = QCheckBox("已掌握")
        self.mastered_checkbox.stateChanged.connect(self.on_mastered_changed)
        status_layout.addWidget(self.mastered_checkbox)

        self.review_count_label = QLabel()
        status_layout.addWidget(self.review_count_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        layout.addStretch()

        return widget

    def create_bottom_buttons(self) -> QHBoxLayout:
        """创建底部按钮"""
        layout = QHBoxLayout()

        # 开始复习按钮
        review_btn = QPushButton("开始复习选中项")
        review_btn.clicked.connect(self.on_start_review)
        layout.addWidget(review_btn)

        # 导出按钮
        export_btn = QPushButton("导出错题")
        export_btn.clicked.connect(self.on_export)
        layout.addWidget(export_btn)

        layout.addStretch()

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        return layout

    def load_mistakes(self):
        """加载错题"""
        try:
            self.current_mistakes = self.mistake_book.get_student_mistakes(
                self.student_id
            )
            self.update_table()
            self.update_statistics()
        except Exception as e:
            logger.error(f"加载错题失败: {e}")
            QMessageBox.warning(self, "错误", f"加载错题失败: {e}")

    def apply_filters(self):
        """应用筛选"""
        mistake_type = self.type_filter.currentData()
        reviewed = self.status_filter.currentData()

        try:
            self.current_mistakes = self.mistake_book.get_student_mistakes(
                self.student_id,
                reviewed=reviewed,
                mistake_type=mistake_type if mistake_type else None,
            )
            self.update_table()
            self.update_statistics()
        except Exception as e:
            logger.error(f"筛选错题失败: {e}")

    def update_table(self):
        """更新表格"""
        self.table.setRowCount(0)

        for mistake in self.current_mistakes:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # 日期
            date_str = mistake.occurred_at[:10] if mistake.occurred_at else ""
            self.table.setItem(row, 0, QTableWidgetItem(date_str))

            # 实验
            self.table.setItem(row, 1, QTableWidgetItem(mistake.experiment_name))

            # 类型
            type_map = {
                "operation": "操作",
                "calculation": "计算",
                "concept": "概念",
                "safety": "安全",
                "other": "其他",
            }
            type_str = type_map.get(mistake.mistake_type, mistake.mistake_type)
            self.table.setItem(row, 2, QTableWidgetItem(type_str))

            # 描述
            self.table.setItem(row, 3, QTableWidgetItem(mistake.mistake_description))

            # 状态
            status_item = QTableWidgetItem("✓" if mistake.reviewed else "✗")
            if mistake.reviewed:
                status_item.setForeground(QColor("green"))
            else:
                status_item.setForeground(QColor("red"))
            self.table.setItem(row, 4, status_item)

            # 掌握
            mastered_item = QTableWidgetItem("✓" if mistake.mastered else "✗")
            if mistake.mastered:
                mastered_item.setForeground(QColor("green"))
            self.table.setItem(row, 5, mastered_item)

            # 存储错题ID
            self.table.item(row, 0).setData(
                Qt.ItemDataRole.UserRole, mistake.mistake_id
            )

    def update_statistics(self):
        """更新统计信息"""
        stats = self.mistake_book.get_statistics(self.student_id)

        self.stats_label.setText(
            f"总计: {stats['total']} | "
            f"已复习: {stats['reviewed']} | "
            f"已掌握: {stats['mastered']} | "
            f"复习率: {stats['review_rate']}%"
        )

    def on_cell_double_clicked(self, row, _column):
        """单元格双击事件"""
        self.show_mistake_detail(row)

    def on_selection_changed(self):
        """选择变化事件"""
        selected_rows = self.table.selectionModel().selectedRows()

        if selected_rows:
            row = selected_rows[0].row()
            self.show_mistake_detail(row)

    def show_mistake_detail(self, row: int):
        """显示错误详情"""
        if row < 0 or row >= len(self.current_mistakes):
            return

        mistake = self.current_mistakes[row]
        self.selected_mistake = mistake

        # 更新详情面板
        self.exp_label.setText(f"实验: {mistake.experiment_name}")

        type_map = {
            "operation": "操作错误",
            "calculation": "计算错误",
            "concept": "概念错误",
            "safety": "安全错误",
            "other": "其他错误",
        }
        self.type_label.setText(
            f"类型: {type_map.get(mistake.mistake_type, mistake.mistake_type)}"
        )
        self.date_label.setText(f"发生时间: {mistake.occurred_at[:19]}")

        self.desc_text.setPlainText(mistake.mistake_description)
        self.correct_answer_text.setPlainText(mistake.correct_answer)
        self.student_answer_text.setPlainText(mistake.student_answer)

        # 阻止信号触发
        self.reviewed_checkbox.blockSignals(True)
        self.mastered_checkbox.blockSignals(True)

        self.reviewed_checkbox.setChecked(mistake.reviewed)
        self.mastered_checkbox.setChecked(mistake.mastered)

        self.reviewed_checkbox.blockSignals(False)
        self.mastered_checkbox.blockSignals(False)

        self.review_count_label.setText(f"复习次数: {mistake.review_count}")

    def on_reviewed_changed(self, _state):
        """复习状态改变"""
        if self.selected_mistake:
            self.mistake_book.mark_as_reviewed(
                self.selected_mistake.mistake_id,
                self.student_id,
                mastered=self.mastered_checkbox.isChecked(),
            )
            self.load_mistakes()

    def on_mastered_changed(self, state):
        """掌握状态改变"""
        if self.selected_mistake:
            mastered = state == Qt.CheckState.Checked
            if mastered:
                # 如果标记为掌握，自动标记为已复习
                self.reviewed_checkbox.setChecked(True)

            self.mistake_book.mark_as_reviewed(
                self.selected_mistake.mistake_id, self.student_id, mastered=mastered
            )
            self.load_mistakes()

    def on_start_review(self):
        """开始复习"""
        selected_rows = self.table.selectionModel().selectedRows()

        if not selected_rows:
            QMessageBox.information(self, "提示", "请选择要复习的错题")
            return

        mistake_ids = []
        for row in selected_rows:
            mistake_id = self.table.item(row.row(), 0).data(Qt.ItemDataRole.UserRole)
            mistake_ids.append(mistake_id)

        self.start_review.emit(mistake_ids)
        self.accept()

    def on_export(self):
        """导出错题"""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出错题",
            f"错题本_{self.student_id}_{datetime.now().strftime('%Y%m%d')}.json",
            "JSON Files (*.json);;CSV Files (*.csv)",
        )

        if file_path:
            format_type = "csv" if file_path.endswith(".csv") else "json"
            success = self.mistake_book.export_mistakes(
                self.student_id, Path(file_path), format=format_type
            )

            if success:
                QMessageBox.information(self, "成功", "错题已导出")
            else:
                QMessageBox.warning(self, "失败", "导出失败")
