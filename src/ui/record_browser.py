"""
记录浏览器
查看和管理历史实验记录
"""

from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from ..models.user_record import UserRecord
from ..report.report_generator import ReportGenerator
from ..storage.json_store import JSONStore
from ..utils.i18n import I18n
from ..utils.logger import get_logger

from .html_utils import escape_html

logger = get_logger(__name__)


class RecordBrowser(QDialog):
    """记录浏览器窗口"""

    # 信号：请求重做实验
    redo_experiment = Signal(str)  # experiment_id

    def __init__(
        self,
        store: JSONStore,
        user_id: str = "student_001",
        i18n_dir: str = "assets/i18n",
        parent=None,
    ):
        super().__init__(parent)
        self.store = store
        self.user_id = user_id
        self.i18n = I18n(i18n_dir)
        self.report_gen = ReportGenerator(i18n_dir)
        self.current_record: UserRecord | None = None
        self.all_records = []

        self.init_ui()
        self.load_records()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle(self.i18n.t("ui.record_browser_title"))
        self.resize(1000, 700)

        layout = QVBoxLayout(self)

        # 顶部工具栏
        toolbar = self.create_toolbar()
        layout.addLayout(toolbar)

        # 主内容区域（分割器）
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：记录列表
        left_panel = self.create_list_panel()
        splitter.addWidget(left_panel)

        # 右侧：详情面板
        right_panel = self.create_detail_panel()
        splitter.addWidget(right_panel)

        # 设置分割比例
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

        # 底部按钮
        button_layout = self.create_buttons()
        layout.addLayout(button_layout)

    def create_toolbar(self) -> QHBoxLayout:
        """创建工具栏"""
        toolbar = QHBoxLayout()

        # 搜索框
        search_label = QLabel(self.i18n.t("ui.search") + ":")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.i18n.t("ui.search_placeholder"))
        self.search_input.textChanged.connect(self.on_search)

        # 实验类型筛选
        filter_label = QLabel(self.i18n.t("ui.experiment_type") + ":")
        self.filter_combo = QComboBox()
        self.filter_combo.addItem(self.i18n.t("ui.all"), None)
        self.filter_combo.currentIndexChanged.connect(self.on_filter_changed)

        # 刷新按钮
        refresh_btn = QPushButton(self.i18n.t("ui.refresh"))
        refresh_btn.clicked.connect(self.load_records)

        toolbar.addWidget(search_label)
        toolbar.addWidget(self.search_input, 2)
        toolbar.addWidget(filter_label)
        toolbar.addWidget(self.filter_combo, 1)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()

        return toolbar

    def create_list_panel(self) -> QGroupBox:
        """创建列表面板"""
        group = QGroupBox(self.i18n.t("ui.experiment_records"))
        layout = QVBoxLayout(group)

        # 记录表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            [
                self.i18n.t("ui.experiment_title"),
                self.i18n.t("ui.score"),
                self.i18n.t("ui.date"),
                self.i18n.t("ui.duration"),
                self.i18n.t("ui.status"),
            ]
        )

        # 表格样式
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        # 自动调整列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        # 选择事件
        self.table.itemSelectionChanged.connect(self.on_record_selected)

        layout.addWidget(self.table)

        return group

    def create_detail_panel(self) -> QGroupBox:
        """创建详情面板"""
        group = QGroupBox(self.i18n.t("ui.record_details"))
        layout = QVBoxLayout(group)

        # 基本信息
        self.info_label = QLabel(self.i18n.t("ui.no_record_selected"))
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # 步骤记录
        steps_label = QLabel(self.i18n.t("ui.step_records") + ":")
        steps_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(steps_label)

        self.steps_text = QTextEdit()
        self.steps_text.setReadOnly(True)
        layout.addWidget(self.steps_text)

        # 错误汇总
        errors_label = QLabel(self.i18n.t("ui.error_summary") + ":")
        errors_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(errors_label)

        self.errors_text = QTextEdit()
        self.errors_text.setReadOnly(True)
        self.errors_text.setMaximumHeight(120)
        layout.addWidget(self.errors_text)

        return group

    def create_buttons(self) -> QHBoxLayout:
        """创建底部按钮"""
        button_layout = QHBoxLayout()

        # 删除按钮
        self.delete_btn = QPushButton(self.i18n.t("ui.delete_record"))
        self.delete_btn.clicked.connect(self.on_delete)
        self.delete_btn.setEnabled(False)

        # 导出报告按钮
        self.export_btn = QPushButton(self.i18n.t("ui.export_report"))
        self.export_btn.clicked.connect(self.on_export_report)
        self.export_btn.setEnabled(False)

        # 重做实验按钮
        self.redo_btn = QPushButton(self.i18n.t("ui.redo_experiment"))
        self.redo_btn.clicked.connect(self.on_redo)
        self.redo_btn.setEnabled(False)

        # 关闭按钮
        close_btn = QPushButton(self.i18n.t("ui.close"))
        close_btn.clicked.connect(self.accept)

        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.redo_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        return button_layout

    def load_records(self):
        """加载记录列表"""
        try:
            # 加载所有记录
            self.all_records = self.store.list_records(user_id=self.user_id)

            # 更新筛选下拉框
            self.update_filter_options()

            # 显示记录
            self.display_records(self.all_records)

            logger.info(f"加载了 {len(self.all_records)} 条记录")

        except Exception as e:
            logger.error(f"加载记录失败: {e}")
            QMessageBox.critical(
                self,
                self.i18n.t("error.title"),
                self.i18n.t("error.load_records_failed", error=str(e)),
            )

    def update_filter_options(self):
        """更新筛选选项"""
        # 获取所有实验类型
        experiment_types = set()
        for record in self.all_records:
            exp_title = record.get("experiment_title", record.get("experiment_id", ""))
            experiment_types.add(exp_title)

        # 更新下拉框
        current_filter = self.filter_combo.currentData()
        self.filter_combo.clear()
        self.filter_combo.addItem(self.i18n.t("ui.all"), None)

        for exp_type in sorted(experiment_types):
            self.filter_combo.addItem(exp_type, exp_type)

        # 恢复之前的选择
        if current_filter:
            index = self.filter_combo.findData(current_filter)
            if index >= 0:
                self.filter_combo.setCurrentIndex(index)

    def display_records(self, records: list):
        """显示记录列表"""
        self.table.setRowCount(len(records))

        for row, record in enumerate(records):
            # 实验标题
            title = record.get("experiment_title", record.get("experiment_id", ""))
            self.table.setItem(row, 0, QTableWidgetItem(title))

            # 得分
            score = record.get("final_score", 0)
            score_item = QTableWidgetItem(f"{score:.1f}")
            score_item.setTextAlignment(Qt.AlignCenter)

            # 根据分数设置颜色
            if score >= 90:
                score_item.setForeground(QColor("#2E7D32"))  # 绿色
            elif score >= 70:
                score_item.setForeground(QColor("#F57C00"))  # 橙色
            else:
                score_item.setForeground(QColor("#C62828"))  # 红色

            self.table.setItem(row, 1, score_item)

            # 日期
            started_at = record.get("started_at", "")
            if started_at:
                try:
                    dt = datetime.fromisoformat(started_at)
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    date_str = started_at
            else:
                date_str = ""
            self.table.setItem(row, 2, QTableWidgetItem(date_str))

            # 时长
            duration_str = self.calculate_duration(record)
            duration_item = QTableWidgetItem(duration_str)
            duration_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, duration_item)

            # 状态
            status = (
                self.i18n.t("ui.completed")
                if record.get("finished_at")
                else self.i18n.t("ui.incomplete")
            )
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, status_item)

            # 存储record_id到行数据
            self.table.item(row, 0).setData(Qt.UserRole, record.get("record_id"))

    def calculate_duration(self, record: dict[str, Any]) -> str:
        """计算实验时长"""
        started_at = record.get("started_at")
        finished_at = record.get("finished_at")

        if not started_at or not finished_at:
            return "-"

        try:
            start = datetime.fromisoformat(started_at)
            end = datetime.fromisoformat(finished_at)
            duration = (end - start).total_seconds()

            minutes = int(duration // 60)
            seconds = int(duration % 60)

            return f"{minutes}分{seconds}秒"
        except Exception:
            return "-"

    def on_search(self, query: str):
        """搜索记录"""
        if not query:
            # 显示所有记录（应用筛选）
            self.on_filter_changed()
            return

        # 搜索匹配的记录
        results = self.store.search_records(query, user_id=self.user_id)
        self.display_records(results)

    def on_filter_changed(self):
        """筛选改变"""
        filter_value = self.filter_combo.currentData()

        if filter_value is None:
            # 显示所有
            self.display_records(self.all_records)
        else:
            # 筛选
            filtered = [
                r
                for r in self.all_records
                if r.get("experiment_title") == filter_value
                or r.get("experiment_id") == filter_value
            ]
            self.display_records(filtered)

    def on_record_selected(self):
        """记录被选中"""
        selected = self.table.selectedItems()
        if not selected:
            self.current_record = None
            self.update_detail_panel(None)
            self.delete_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            self.redo_btn.setEnabled(False)
            return

        # 获取record_id
        record_id = self.table.item(selected[0].row(), 0).data(Qt.UserRole)

        # 加载完整记录
        self.current_record = self.store.load_record(self.user_id, record_id)

        # 更新详情面板
        self.update_detail_panel(self.current_record)

        # 启用按钮
        self.delete_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.redo_btn.setEnabled(True)

    def update_detail_panel(self, record: UserRecord | None):
        """更新详情面板"""
        if not record:
            self.info_label.setText(self.i18n.t("ui.no_record_selected"))
            self.steps_text.clear()
            self.errors_text.clear()
            return

        # 基本信息
        title = escape_html(getattr(record, "experiment_title", record.experiment_id))
        record_id = escape_html(record.record_id)
        user_id = escape_html(record.user_id)
        started_at = escape_html(record.started_at.strftime("%Y-%m-%d %H:%M:%S"))
        finished_at = escape_html(
            record.finished_at.strftime("%Y-%m-%d %H:%M:%S")
            if record.finished_at
            else self.i18n.t("ui.incomplete")
        )
        score_color = (
            "#2E7D32"
            if record.final_score >= 90
            else "#F57C00"
            if record.final_score >= 70
            else "#C62828"
        )
        info_html = f"""
        <h3>{title}</h3>
        <p><b>{escape_html(self.i18n.t("ui.record_id"))}:</b> {record_id}</p>
        <p><b>{escape_html(self.i18n.t("ui.user_id"))}:</b> {user_id}</p>
        <p><b>{escape_html(self.i18n.t("ui.final_score"))}:</b> <span style='color: {score_color}'>{record.final_score:.1f}</span></p>
        <p><b>{escape_html(self.i18n.t("ui.started_at"))}:</b> {started_at}</p>
        <p><b>{escape_html(self.i18n.t("ui.finished_at"))}:</b> {finished_at}</p>
        """
        self.info_label.setText(info_html)

        # 步骤记录
        steps_html = ""
        for step in record.step_records:
            icon = "✅" if step.passed else "❌"
            steps_html += (
                f"{icon} <b>{escape_html(step.step_id)}</b> - "
                f"{escape_html(self.i18n.t('ui.score'))}: {escape_html(step.score)}<br>"
            )
        self.steps_text.setHtml(steps_html)

        # 错误汇总
        if record.mistakes:
            errors_html = (
                "<p style='color: #C62828'><b>"
                f"{escape_html(self.i18n.t('ui.total_errors'))}: {len(record.mistakes)}"
                "</b></p>"
            )
            for mistake in record.mistakes[:10]:  # 最多显示10条
                errors_html += (
                    f"• {escape_html(mistake.step_id)}: {escape_html(mistake.message)}<br>"
                )
            self.errors_text.setHtml(errors_html)
        else:
            self.errors_text.setHtml(
                f"<p style='color: #2E7D32'>{escape_html(self.i18n.t('ui.no_errors'))}</p>"
            )

    def on_delete(self):
        """删除记录"""
        if not self.current_record:
            return

        # 确认删除
        reply = QMessageBox.question(
            self,
            self.i18n.t("ui.confirm_delete"),
            self.i18n.t(
                "ui.confirm_delete_message", record_id=self.current_record.record_id
            ),
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            if self.store.delete_record(self.user_id, self.current_record.record_id):
                QMessageBox.information(
                    self, self.i18n.t("ui.success"), self.i18n.t("ui.delete_success")
                )
                self.load_records()
            else:
                QMessageBox.critical(
                    self, self.i18n.t("error.title"), self.i18n.t("error.delete_failed")
                )

    def on_export_report(self):
        """导出报告"""
        if not self.current_record:
            return

        from PySide6.QtWidgets import QFileDialog

        # 选择保存位置和格式
        filename, filter_type = QFileDialog.getSaveFileName(
            self,
            self.i18n.t("ui.export_report"),
            f"report_{self.current_record.record_id}.html",
            "HTML Files (*.html);;PDF Files (*.pdf)",
        )

        if filename:
            try:
                # 确保扩展名后再校验保存路径
                if not filename.endswith(".pdf") and not filename.endswith(".html"):
                    filename += ".html"
                from .path_security import validate_dialog_path

                filename = str(validate_dialog_path(filename))

                # 根据选择的格式导出
                if filename.endswith(".pdf"):
                    self.report_gen.generate_pdf_report(self.current_record, filename)
                else:
                    self.report_gen.generate_html_report(self.current_record, filename)

                QMessageBox.information(
                    self,
                    self.i18n.t("ui.success"),
                    self.i18n.t("ui.export_success", filename=filename),
                )
            except ImportError as e:
                logger.error(f"导出PDF失败: {e}")
                QMessageBox.critical(
                    self,
                    self.i18n.t("error.title"),
                    "PDF导出需要安装weasyprint库。\n请运行: pip install weasyprint",
                )
            except Exception as e:
                logger.error(f"导出报告失败: {e}")
                QMessageBox.critical(
                    self,
                    self.i18n.t("error.title"),
                    self.i18n.t("error.export_failed", error=str(e)),
                )

    def on_redo(self):
        """重做实验"""
        if not self.current_record:
            return

        # 发送信号请求重做实验
        self.redo_experiment.emit(self.current_record.experiment_id)
        self.accept()
