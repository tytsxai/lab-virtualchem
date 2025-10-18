"""
实验模板创建向导
提供图形化界面来创建和编辑实验模板
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.template_engine import TemplateEngine
from ..models.experiment import (
    ExperimentTemplate,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TemplateWizard(QDialog):
    """实验模板创建向导"""

    template_created = Signal(str)  # 模板创建完成信号

    def __init__(self, parent=None, template_engine: TemplateEngine = None):
        super().__init__(parent)
        self.template_engine = template_engine
        self.current_template = None
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("实验模板创建向导")
        self.setModal(True)
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 基本信息标签页
        self.basic_info_tab = self.create_basic_info_tab()
        self.tab_widget.addTab(self.basic_info_tab, "基本信息")

        # 试剂信息标签页
        self.reagents_tab = self.create_reagents_tab()
        self.tab_widget.addTab(self.reagents_tab, "试剂")

        # 实验步骤标签页
        self.steps_tab = self.create_steps_tab()
        self.tab_widget.addTab(self.steps_tab, "实验步骤")

        # 评分规则标签页
        self.scoring_tab = self.create_scoring_tab()
        self.tab_widget.addTab(self.scoring_tab, "评分规则")

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(button_box)

        button_box.accepted.connect(self.save_template)
        button_box.rejected.connect(self.reject)

    def create_basic_info_tab(self) -> QWidget:
        """创建基本信息标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)

        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("例如: titration_naoh_hcl_v1")
        basic_layout.addRow("实验ID:", self.id_edit)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("例如: NaOH滴定HCl实验")
        basic_layout.addRow("实验标题:", self.title_edit)

        self.title_en_edit = QLineEdit()
        self.title_en_edit.setPlaceholderText("例如: NaOH Titration of HCl")
        basic_layout.addRow("英文标题:", self.title_en_edit)

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("实验描述...")
        basic_layout.addRow("实验描述:", self.description_edit)

        # 分类和难度组
        category_group = QGroupBox("分类和难度")
        category_layout = QFormLayout(category_group)

        self.category_combo = QComboBox()
        self.category_combo.addItems(
            ["titration", "precipitation", "distillation", "recrystallization", "esterification", "buffer", "other"]
        )
        category_layout.addRow("实验分类:", self.category_combo)

        self.level_combo = QComboBox()
        self.level_combo.addItems(["basic", "intermediate", "advanced"])
        category_layout.addRow("难度等级:", self.level_combo)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(10, 300)
        self.duration_spin.setValue(45)
        self.duration_spin.setSuffix(" 分钟")
        category_layout.addRow("预计时长:", self.duration_spin)

        # 实验目标组
        goals_group = QGroupBox("实验目标")
        goals_layout = QVBoxLayout(goals_group)

        self.goals_list = QListWidget()
        goals_layout.addWidget(self.goals_list)

        goals_buttons = QHBoxLayout()
        self.add_goal_btn = QPushButton("添加目标")
        self.remove_goal_btn = QPushButton("删除目标")
        goals_buttons.addWidget(self.add_goal_btn)
        goals_buttons.addWidget(self.remove_goal_btn)
        goals_buttons.addStretch()
        goals_layout.addLayout(goals_buttons)

        layout.addWidget(basic_group)
        layout.addWidget(category_group)
        layout.addWidget(goals_group)
        layout.addStretch()

        return widget

    def create_reagents_tab(self) -> QWidget:
        """创建试剂信息标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 试剂列表
        reagents_group = QGroupBox("试剂列表")
        reagents_layout = QVBoxLayout(reagents_group)

        self.reagents_list = QListWidget()
        reagents_layout.addWidget(self.reagents_list)

        # 试剂操作按钮
        reagents_buttons = QHBoxLayout()
        self.add_reagent_btn = QPushButton("添加试剂")
        self.edit_reagent_btn = QPushButton("编辑试剂")
        self.remove_reagent_btn = QPushButton("删除试剂")

        reagents_buttons.addWidget(self.add_reagent_btn)
        reagents_buttons.addWidget(self.edit_reagent_btn)
        reagents_buttons.addWidget(self.remove_reagent_btn)
        reagents_buttons.addStretch()
        reagents_layout.addLayout(reagents_buttons)

        layout.addWidget(reagents_group)
        layout.addStretch()

        return widget

    def create_steps_tab(self) -> QWidget:
        """创建实验步骤标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 步骤列表
        steps_group = QGroupBox("实验步骤")
        steps_layout = QVBoxLayout(steps_group)

        self.steps_list = QListWidget()
        steps_layout.addWidget(self.steps_list)

        # 步骤操作按钮
        steps_buttons = QHBoxLayout()
        self.add_step_btn = QPushButton("添加步骤")
        self.edit_step_btn = QPushButton("编辑步骤")
        self.remove_step_btn = QPushButton("删除步骤")
        self.move_up_btn = QPushButton("上移")
        self.move_down_btn = QPushButton("下移")

        steps_buttons.addWidget(self.add_step_btn)
        steps_buttons.addWidget(self.edit_step_btn)
        steps_buttons.addWidget(self.remove_step_btn)
        steps_buttons.addWidget(self.move_up_btn)
        steps_buttons.addWidget(self.move_down_btn)
        steps_buttons.addStretch()
        steps_layout.addLayout(steps_buttons)

        layout.addWidget(steps_group)
        layout.addStretch()

        return widget

    def create_scoring_tab(self) -> QWidget:
        """创建评分规则标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 评分规则列表
        scoring_group = QGroupBox("评分规则")
        scoring_layout = QVBoxLayout(scoring_group)

        self.scoring_list = QListWidget()
        scoring_layout.addWidget(self.scoring_list)

        # 评分规则操作按钮
        scoring_buttons = QHBoxLayout()
        self.add_scoring_btn = QPushButton("添加规则")
        self.edit_scoring_btn = QPushButton("编辑规则")
        self.remove_scoring_btn = QPushButton("删除规则")

        scoring_buttons.addWidget(self.add_scoring_btn)
        scoring_buttons.addWidget(self.edit_scoring_btn)
        scoring_buttons.addWidget(self.remove_scoring_btn)
        scoring_buttons.addStretch()
        scoring_layout.addLayout(scoring_buttons)

        layout.addWidget(scoring_group)
        layout.addStretch()

        return widget

    def setup_connections(self):
        """设置信号连接"""
        # 目标操作
        self.add_goal_btn.clicked.connect(self.add_goal)
        self.remove_goal_btn.clicked.connect(self.remove_goal)

        # 试剂操作
        self.add_reagent_btn.clicked.connect(self.add_reagent)
        self.edit_reagent_btn.clicked.connect(self.edit_reagent)
        self.remove_reagent_btn.clicked.connect(self.remove_reagent)

        # 步骤操作
        self.add_step_btn.clicked.connect(self.add_step)
        self.edit_step_btn.clicked.connect(self.edit_step)
        self.remove_step_btn.clicked.connect(self.remove_step)
        self.move_up_btn.clicked.connect(self.move_step_up)
        self.move_down_btn.clicked.connect(self.move_step_down)

        # 评分规则操作
        self.add_scoring_btn.clicked.connect(self.add_scoring_rule)
        self.edit_scoring_btn.clicked.connect(self.edit_scoring_rule)
        self.remove_scoring_btn.clicked.connect(self.remove_scoring_rule)

    def add_goal(self):
        """添加实验目标"""
        goal_text, ok = QInputDialog.getText(self, "添加目标", "请输入实验目标:")
        if ok and goal_text.strip():
            item = QListWidgetItem(goal_text.strip())
            self.goals_list.addItem(item)

    def remove_goal(self):
        """删除选中的目标"""
        current_row = self.goals_list.currentRow()
        if current_row >= 0:
            self.goals_list.takeItem(current_row)

    def add_reagent(self):
        """添加试剂"""
        dialog = ReagentDialog(self)
        if dialog.exec() == QDialog.Accepted:
            reagent_data = dialog.get_reagent_data()
            item = QListWidgetItem(f"{reagent_data['name']} ({reagent_data['formula']})")
            item.setData(Qt.ItemDataRole.UserRole, reagent_data)
            self.reagents_list.addItem(item)

    def edit_reagent(self):
        """编辑选中的试剂"""
        current_item = self.reagents_list.currentItem()
        if not current_item:
            return

        reagent_data = current_item.data(Qt.ItemDataRole.UserRole)
        dialog = ReagentDialog(self, reagent_data)
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_reagent_data()
            current_item.setText(f"{new_data['name']} ({new_data['formula']})")
            current_item.setData(Qt.ItemDataRole.UserRole, new_data)

    def remove_reagent(self):
        """删除选中的试剂"""
        current_row = self.reagents_list.currentRow()
        if current_row >= 0:
            self.reagents_list.takeItem(current_row)

    def add_step(self):
        """添加实验步骤"""
        dialog = StepDialog(self)
        if dialog.exec() == QDialog.Accepted:
            step_data = dialog.get_step_data()
            item = QListWidgetItem(f"步骤 {self.steps_list.count() + 1}: {step_data['title']}")
            item.setData(Qt.ItemDataRole.UserRole, step_data)
            self.steps_list.addItem(item)

    def edit_step(self):
        """编辑选中的步骤"""
        current_item = self.steps_list.currentItem()
        if not current_item:
            return

        step_data = current_item.data(Qt.ItemDataRole.UserRole)
        dialog = StepDialog(self, step_data)
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_step_data()
            current_item.setText(f"步骤 {self.steps_list.currentRow() + 1}: {new_data['title']}")
            current_item.setData(Qt.ItemDataRole.UserRole, new_data)

    def remove_step(self):
        """删除选中的步骤"""
        current_row = self.steps_list.currentRow()
        if current_row >= 0:
            self.steps_list.takeItem(current_row)
            # 重新编号
            for i in range(self.steps_list.count()):
                item = self.steps_list.item(i)
                step_data = item.data(Qt.ItemDataRole.UserRole)
                item.setText(f"步骤 {i + 1}: {step_data['title']}")

    def move_step_up(self):
        """上移步骤"""
        current_row = self.steps_list.currentRow()
        if current_row > 0:
            item = self.steps_list.takeItem(current_row)
            self.steps_list.insertItem(current_row - 1, item)
            self.steps_list.setCurrentRow(current_row - 1)
            self.update_step_numbers()

    def move_step_down(self):
        """下移步骤"""
        current_row = self.steps_list.currentRow()
        if current_row < self.steps_list.count() - 1:
            item = self.steps_list.takeItem(current_row)
            self.steps_list.insertItem(current_row + 1, item)
            self.steps_list.setCurrentRow(current_row + 1)
            self.update_step_numbers()

    def update_step_numbers(self):
        """更新步骤编号"""
        for i in range(self.steps_list.count()):
            item = self.steps_list.item(i)
            step_data = item.data(Qt.ItemDataRole.UserRole)
            item.setText(f"步骤 {i + 1}: {step_data['title']}")

    def add_scoring_rule(self):
        """添加评分规则"""
        dialog = ScoringRuleDialog(self)
        if dialog.exec() == QDialog.Accepted:
            rule_data = dialog.get_rule_data()
            item = QListWidgetItem(f"{rule_data['name']}: {rule_data['points']}分")
            item.setData(Qt.ItemDataRole.UserRole, rule_data)
            self.scoring_list.addItem(item)

    def edit_scoring_rule(self):
        """编辑选中的评分规则"""
        current_item = self.scoring_list.currentItem()
        if not current_item:
            return

        rule_data = current_item.data(Qt.ItemDataRole.UserRole)
        dialog = ScoringRuleDialog(self, rule_data)
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_rule_data()
            current_item.setText(f"{new_data['name']}: {new_data['points']}分")
            current_item.setData(Qt.ItemDataRole.UserRole, new_data)

    def remove_scoring_rule(self):
        """删除选中的评分规则"""
        current_row = self.scoring_list.currentRow()
        if current_row >= 0:
            self.scoring_list.takeItem(current_row)

    def save_template(self):
        """保存模板"""
        try:
            # 验证基本信息
            if not self.id_edit.text().strip():
                QMessageBox.warning(self, "验证失败", "请输入实验ID")
                return

            if not self.title_edit.text().strip():
                QMessageBox.warning(self, "验证失败", "请输入实验标题")
                return

            if self.steps_list.count() == 0:
                QMessageBox.warning(self, "验证失败", "请至少添加一个实验步骤")
                return

            # 收集数据
            template_data = self.collect_template_data()

            # 创建模板对象
            template = ExperimentTemplate(**template_data)

            # 保存到文件
            if self.template_engine:
                template_path = self.template_engine.templates_dir / f"{template.id}.yaml"
                self.template_engine.save_template(template, template_path)

            QMessageBox.information(self, "成功", f"模板已保存: {template.id}")
            self.template_created.emit(template.id)
            self.accept()

        except Exception as e:
            logger.error(f"保存模板失败: {e}")
            QMessageBox.critical(self, "错误", f"保存模板失败: {e}")

    def collect_template_data(self) -> dict[str, Any]:
        """收集模板数据"""
        # 基本信息
        data = {
            "id": self.id_edit.text().strip(),
            "title": self.title_edit.text().strip(),
            "title_en": self.title_en_edit.text().strip() or None,
            "description": self.description_edit.toPlainText().strip(),
            "category": self.category_combo.currentText(),
            "level": self.level_combo.currentText(),
            "duration_min": self.duration_spin.value(),
            "version": "1.0.0",
        }

        # 实验目标
        goals = []
        for i in range(self.goals_list.count()):
            item = self.goals_list.item(i)
            goals.append({"description": item.text()})
        data["goals"] = goals

        # 试剂
        reagents = []
        for i in range(self.reagents_list.count()):
            item = self.reagents_list.item(i)
            reagent_data = item.data(Qt.ItemDataRole.UserRole)
            reagents.append(reagent_data)
        data["reagents"] = reagents

        # 实验步骤
        steps = []
        for i in range(self.steps_list.count()):
            item = self.steps_list.item(i)
            step_data = item.data(Qt.ItemDataRole.UserRole)
            step_data["order"] = i + 1
            steps.append(step_data)
        data["steps"] = steps

        # 评分规则
        score_rules = []
        for i in range(self.scoring_list.count()):
            item = self.scoring_list.item(i)
            rule_data = item.data(Qt.ItemDataRole.UserRole)
            score_rules.append(rule_data)
        data["score_rules"] = score_rules

        return data


class ReagentDialog(QDialog):
    """试剂编辑对话框"""

    def __init__(self, parent=None, reagent_data: dict = None):
        super().__init__(parent)
        self.reagent_data = reagent_data or {}
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("编辑试剂")
        self.setModal(True)
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.name_edit = QLineEdit(self.reagent_data.get("name", ""))
        form_layout.addRow("试剂名称:", self.name_edit)

        self.formula_edit = QLineEdit(self.reagent_data.get("formula", ""))
        form_layout.addRow("化学式:", self.formula_edit)

        self.concentration_edit = QLineEdit(self.reagent_data.get("concentration", ""))
        form_layout.addRow("浓度:", self.concentration_edit)

        self.hazard_level_combo = QComboBox()
        self.hazard_level_combo.addItems(["info", "warning", "danger", "severe"])
        self.hazard_level_combo.setCurrentText(self.reagent_data.get("hazard_level", "info"))
        form_layout.addRow("危害等级:", self.hazard_level_combo)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    def get_reagent_data(self) -> dict[str, Any]:
        """获取试剂数据"""
        return {
            "name": self.name_edit.text().strip(),
            "formula": self.formula_edit.text().strip(),
            "concentration": self.concentration_edit.text().strip(),
            "hazard_level": self.hazard_level_combo.currentText(),
        }


class StepDialog(QDialog):
    """步骤编辑对话框"""

    def __init__(self, parent=None, step_data: dict = None):
        super().__init__(parent)
        self.step_data = step_data or {}
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("编辑实验步骤")
        self.setModal(True)
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.title_edit = QLineEdit(self.step_data.get("title", ""))
        form_layout.addRow("步骤标题:", self.title_edit)

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        self.description_edit.setPlainText(self.step_data.get("description", ""))
        form_layout.addRow("步骤描述:", self.description_edit)

        self.check_type_combo = QComboBox()
        self.check_type_combo.addItems(["no_check", "confirm", "input", "select", "sequence"])
        self.check_type_combo.setCurrentText(self.step_data.get("check_type", "no_check"))
        form_layout.addRow("检查类型:", self.check_type_combo)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    def get_step_data(self) -> dict[str, Any]:
        """获取步骤数据"""
        return {
            "title": self.title_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
            "check_type": self.check_type_combo.currentText(),
            "order": self.step_data.get("order", 1),
        }


class ScoringRuleDialog(QDialog):
    """评分规则编辑对话框"""

    def __init__(self, parent=None, rule_data: dict = None):
        super().__init__(parent)
        self.rule_data = rule_data or {}
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("编辑评分规则")
        self.setModal(True)
        self.resize(400, 200)

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.name_edit = QLineEdit(self.rule_data.get("name", ""))
        form_layout.addRow("规则名称:", self.name_edit)

        self.points_spin = QSpinBox()
        self.points_spin.setRange(0, 100)
        self.points_spin.setValue(self.rule_data.get("points", 10))
        form_layout.addRow("分数:", self.points_spin)

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setPlainText(self.rule_data.get("description", ""))
        form_layout.addRow("规则描述:", self.description_edit)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    def get_rule_data(self) -> dict[str, Any]:
        """获取规则数据"""
        return {
            "name": self.name_edit.text().strip(),
            "points": self.points_spin.value(),
            "description": self.description_edit.toPlainText().strip(),
        }


if __name__ == "__main__":
    app = QApplication([])
    wizard = TemplateWizard()
    wizard.show()
    app.exec()
