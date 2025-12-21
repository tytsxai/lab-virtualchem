"""
配置对话框
提供用户友好的配置界面
"""

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.config_manager import get_config_manager
from ..utils.logger import get_logger
from .modern_widgets import ModernButton
from .themes import ThemeManager

logger = get_logger(__name__)


class ConfigDialog(QDialog):
    """配置对话框"""

    # 信号
    config_changed = Signal(dict)  # 配置改变信号

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.config_manager = get_config_manager()
        self.theme_manager = ThemeManager()  # type: ignore

        self.setWindowTitle("配置设置")
        self.setMinimumSize(600, 500)
        self.setModal(True)

        self.init_ui()
        self.load_current_config()
        self.apply_theme()

        logger.info("配置对话框初始化完成")

    def init_ui(self) -> None:
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel("⚙️ 配置设置")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 选项卡
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 创建各个配置页面
        self.create_general_tab()
        self.create_ui_tab()
        self.create_game_tab()
        self.create_experiment_tab()
        self.create_paths_tab()
        self.create_logging_tab()

        # 按钮
        button_layout = QHBoxLayout()

        # 重置按钮
        self.reset_button = ModernButton("🔄 重置默认")
        self.reset_button.clicked.connect(self.reset_to_default)
        button_layout.addWidget(self.reset_button)

        # 导入/导出按钮
        self.import_button = ModernButton("📥 导入")
        self.import_button.clicked.connect(self.import_config)
        button_layout.addWidget(self.import_button)

        self.export_button = ModernButton("📤 导出")
        self.export_button.clicked.connect(self.export_config)
        button_layout.addWidget(self.export_button)

        button_layout.addStretch()

        # 标准按钮
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        button_layout.addWidget(self.button_box)

        layout.addLayout(button_layout)

    def create_general_tab(self) -> QWidget:
        """创建常规配置页面"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # 应用设置
        app_group = QGroupBox("应用设置")
        app_layout = QFormLayout(app_group)

        # 语言
        self.language_combo = QComboBox()
        self.language_combo.addItems(["zh_CN", "en_US"])
        app_layout.addRow("语言:", self.language_combo)

        # 主题
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light", "auto"])
        app_layout.addRow("主题:", self.theme_combo)

        # 窗口设置
        window_group = QGroupBox("窗口设置")
        window_layout = QFormLayout(window_group)

        # 默认窗口大小
        size_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(800, 2000)
        self.width_spin.setValue(1200)
        size_layout.addWidget(self.width_spin)
        size_layout.addWidget(QLabel("×"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(600, 1500)
        self.height_spin.setValue(800)
        size_layout.addWidget(self.height_spin)
        window_layout.addRow("默认大小:", size_layout)

        # 启动时最大化
        self.maximized_checkbox = QCheckBox("启动时最大化窗口")
        window_layout.addRow(self.maximized_checkbox)

        layout.addWidget(app_group)
        layout.addWidget(window_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "常规")
        return tab

    def create_ui_tab(self) -> QWidget:
        """创建UI配置页面"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # 字体设置
        font_group = QGroupBox("字体设置")
        font_layout = QFormLayout(font_group)

        # 字体族
        self.font_family_edit = QLineEdit()
        self.font_family_edit.setText("Arial")
        font_layout.addRow("字体族:", self.font_family_edit)

        # 字体大小
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(12)
        font_layout.addRow("字体大小:", self.font_size_spin)

        # 效果设置
        effect_group = QGroupBox("效果设置")
        effect_layout = QFormLayout(effect_group)

        # 动画
        self.animation_checkbox = QCheckBox("启用动画效果")
        self.animation_checkbox.setChecked(True)
        effect_layout.addRow(self.animation_checkbox)

        # 音效
        self.sound_checkbox = QCheckBox("启用音效")
        self.sound_checkbox.setChecked(True)
        effect_layout.addRow(self.sound_checkbox)

        # 粒子效果
        self.particle_checkbox = QCheckBox("启用粒子效果")
        self.particle_checkbox.setChecked(True)
        effect_layout.addRow(self.particle_checkbox)

        layout.addWidget(font_group)
        layout.addWidget(effect_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "界面")
        return tab

    def create_game_tab(self) -> QWidget:
        """创建游戏配置页面"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # 物理设置
        physics_group = QGroupBox("物理设置")
        physics_layout = QFormLayout(physics_group)

        # 物理模拟
        self.physics_checkbox = QCheckBox("启用物理模拟")
        self.physics_checkbox.setChecked(True)
        physics_layout.addRow(self.physics_checkbox)

        # 重力强度
        gravity_layout = QHBoxLayout()
        self.gravity_slider = QSlider(Qt.Orientation.Horizontal)
        self.gravity_slider.setRange(0, 100)
        self.gravity_slider.setValue(50)
        self.gravity_label = QLabel("50%")
        self.gravity_slider.valueChanged.connect(
            lambda v: self.gravity_label.setText(f"{v}%")
        )
        gravity_layout.addWidget(self.gravity_slider)
        gravity_layout.addWidget(self.gravity_label)
        physics_layout.addRow("重力强度:", gravity_layout)

        # 摩擦力
        friction_layout = QHBoxLayout()
        self.friction_slider = QSlider(Qt.Orientation.Horizontal)
        self.friction_slider.setRange(0, 100)
        self.friction_slider.setValue(90)
        self.friction_label = QLabel("90%")
        self.friction_slider.valueChanged.connect(
            lambda v: self.friction_label.setText(f"{v}%")
        )
        friction_layout.addWidget(self.friction_slider)
        friction_layout.addWidget(self.friction_label)
        physics_layout.addRow("摩擦力:", friction_layout)

        # 弹跳系数
        bounce_layout = QHBoxLayout()
        self.bounce_slider = QSlider(Qt.Orientation.Horizontal)
        self.bounce_slider.setRange(0, 100)
        self.bounce_slider.setValue(60)
        self.bounce_label = QLabel("60%")
        self.bounce_slider.valueChanged.connect(
            lambda v: self.bounce_label.setText(f"{v}%")
        )
        bounce_layout.addWidget(self.bounce_slider)
        bounce_layout.addWidget(self.bounce_label)
        physics_layout.addRow("弹跳系数:", bounce_layout)

        # 碰撞检测
        self.collision_checkbox = QCheckBox("启用碰撞检测")
        self.collision_checkbox.setChecked(True)
        physics_layout.addRow(self.collision_checkbox)

        # 游戏设置
        game_group = QGroupBox("游戏设置")
        game_layout = QFormLayout(game_group)

        # 自动保存
        self.auto_save_checkbox = QCheckBox("启用自动保存")
        self.auto_save_checkbox.setChecked(True)
        game_layout.addRow(self.auto_save_checkbox)

        # 自动保存间隔
        self.auto_save_interval_spin = QSpinBox()
        self.auto_save_interval_spin.setRange(60, 3600)
        self.auto_save_interval_spin.setValue(300)
        self.auto_save_interval_spin.setSuffix(" 秒")
        game_layout.addRow("保存间隔:", self.auto_save_interval_spin)

        layout.addWidget(physics_group)
        layout.addWidget(game_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "游戏")
        return tab

    def create_experiment_tab(self) -> QWidget:
        """创建实验配置页面"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # 实验设置
        experiment_group = QGroupBox("实验设置")
        experiment_layout = QFormLayout(experiment_group)

        # 自动进行
        self.auto_progression_checkbox = QCheckBox("启用自动进行")
        experiment_layout.addRow(self.auto_progression_checkbox)

        # 步骤验证
        self.step_validation_checkbox = QCheckBox("启用步骤验证")
        self.step_validation_checkbox.setChecked(True)
        experiment_layout.addRow(self.step_validation_checkbox)

        # 实时反馈
        self.real_time_feedback_checkbox = QCheckBox("启用实时反馈")
        self.real_time_feedback_checkbox.setChecked(True)
        experiment_layout.addRow(self.real_time_feedback_checkbox)

        # 数据记录
        self.data_logging_checkbox = QCheckBox("启用数据记录")
        self.data_logging_checkbox.setChecked(True)
        experiment_layout.addRow(self.data_logging_checkbox)

        # 备份设置
        backup_group = QGroupBox("备份设置")
        backup_layout = QFormLayout(backup_group)

        # 启用备份
        self.backup_enabled_checkbox = QCheckBox("启用自动备份")
        self.backup_enabled_checkbox.setChecked(True)
        backup_layout.addRow(self.backup_enabled_checkbox)

        layout.addWidget(experiment_group)
        layout.addWidget(backup_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "实验")
        return tab

    def create_paths_tab(self) -> QWidget:
        """创建路径配置页面"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # 路径设置
        paths_group = QGroupBox("路径设置")
        paths_layout = QFormLayout(paths_group)

        # 实验路径
        experiment_layout = QHBoxLayout()
        self.experiment_path_edit = QLineEdit()
        self.experiment_path_edit.setText("experiments")
        experiment_layout.addWidget(self.experiment_path_edit)
        self.experiment_browse_button = ModernButton("浏览")
        self.experiment_browse_button.clicked.connect(
            lambda: self.browse_folder(self.experiment_path_edit)
        )
        experiment_layout.addWidget(self.experiment_browse_button)
        paths_layout.addRow("实验路径:", experiment_layout)

        # 模板路径
        template_layout = QHBoxLayout()
        self.template_path_edit = QLineEdit()
        self.template_path_edit.setText("templates")
        template_layout.addWidget(self.template_path_edit)
        self.template_browse_button = ModernButton("浏览")
        self.template_browse_button.clicked.connect(
            lambda: self.browse_folder(self.template_path_edit)
        )
        template_layout.addWidget(self.template_browse_button)
        paths_layout.addRow("模板路径:", template_layout)

        # 备份路径
        backup_layout = QHBoxLayout()
        self.backup_path_edit = QLineEdit()
        self.backup_path_edit.setText("backups")
        backup_layout.addWidget(self.backup_path_edit)
        self.backup_browse_button = ModernButton("浏览")
        self.backup_browse_button.clicked.connect(
            lambda: self.browse_folder(self.backup_path_edit)
        )
        backup_layout.addWidget(self.backup_browse_button)
        paths_layout.addRow("备份路径:", backup_layout)

        # 日志路径
        log_layout = QHBoxLayout()
        self.log_path_edit = QLineEdit()
        self.log_path_edit.setText("logs")
        log_layout.addWidget(self.log_path_edit)
        self.log_browse_button = ModernButton("浏览")
        self.log_browse_button.clicked.connect(
            lambda: self.browse_folder(self.log_path_edit)
        )
        log_layout.addWidget(self.log_browse_button)
        paths_layout.addRow("日志路径:", log_layout)

        layout.addWidget(paths_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "路径")
        return tab

    def create_logging_tab(self) -> QWidget:
        """创建日志配置页面"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # 日志设置
        logging_group = QGroupBox("日志设置")
        logging_layout = QFormLayout(logging_group)

        # 日志级别
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setCurrentText("INFO")
        logging_layout.addRow("日志级别:", self.log_level_combo)

        # 文件日志
        self.file_logging_checkbox = QCheckBox("启用文件日志")
        self.file_logging_checkbox.setChecked(True)
        logging_layout.addRow(self.file_logging_checkbox)

        # 控制台日志
        self.console_logging_checkbox = QCheckBox("启用控制台日志")
        self.console_logging_checkbox.setChecked(True)
        logging_layout.addRow(self.console_logging_checkbox)

        # 最大文件大小
        self.max_file_size_spin = QSpinBox()
        self.max_file_size_spin.setRange(1, 100)
        self.max_file_size_spin.setValue(10)
        self.max_file_size_spin.setSuffix(" MB")
        logging_layout.addRow("最大文件大小:", self.max_file_size_spin)

        # 备份数量
        self.backup_count_spin = QSpinBox()
        self.backup_count_spin.setRange(1, 20)
        self.backup_count_spin.setValue(5)
        logging_layout.addRow("备份数量:", self.backup_count_spin)

        layout.addWidget(logging_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "日志")
        return tab

    def load_current_config(self) -> None:
        """加载当前配置"""
        try:
            # 应用配置
            app_config = self.config_manager.get_app_config()
            self.language_combo.setCurrentText(app_config.get("language", "zh_CN"))
            self.theme_combo.setCurrentText(app_config.get("theme", "dark"))

            window_config = app_config.get("window", {})
            self.width_spin.setValue(window_config.get("width", 1200))
            self.height_spin.setValue(window_config.get("height", 800))
            self.maximized_checkbox.setChecked(window_config.get("maximized", False))

            # UI配置
            ui_config = self.config_manager.get_ui_config()
            self.font_family_edit.setText(ui_config.get("font_family", "Arial"))
            self.font_size_spin.setValue(ui_config.get("font_size", 12))
            self.animation_checkbox.setChecked(ui_config.get("animation_enabled", True))
            self.sound_checkbox.setChecked(ui_config.get("sound_enabled", True))
            self.particle_checkbox.setChecked(ui_config.get("particle_effects", True))

            # 游戏配置
            game_config = self.config_manager.get_game_config()
            self.physics_checkbox.setChecked(game_config.get("physics_enabled", True))
            self.gravity_slider.setValue(
                int(game_config.get("gravity_strength", 0.5) * 100)
            )
            self.friction_slider.setValue(int(game_config.get("friction", 0.9) * 100))
            self.bounce_slider.setValue(
                int(game_config.get("bounce_factor", 0.6) * 100)
            )
            self.collision_checkbox.setChecked(
                game_config.get("collision_detection", True)
            )
            self.auto_save_checkbox.setChecked(game_config.get("auto_save", True))
            self.auto_save_interval_spin.setValue(
                game_config.get("auto_save_interval", 300)
            )

            # 实验配置
            experiment_config = self.config_manager.get_experiment_config()
            self.auto_progression_checkbox.setChecked(
                experiment_config.get("auto_progression", False)
            )
            self.step_validation_checkbox.setChecked(
                experiment_config.get("step_validation", True)
            )
            self.real_time_feedback_checkbox.setChecked(
                experiment_config.get("real_time_feedback", True)
            )
            self.data_logging_checkbox.setChecked(
                experiment_config.get("data_logging", True)
            )
            self.backup_enabled_checkbox.setChecked(
                experiment_config.get("backup_enabled", True)
            )

            # 路径配置
            paths_config = self.config_manager.get_paths_config()
            self.experiment_path_edit.setText(
                paths_config.get("experiments", "experiments")
            )
            self.template_path_edit.setText(paths_config.get("templates", "templates"))
            self.backup_path_edit.setText(paths_config.get("backups", "backups"))
            self.log_path_edit.setText(paths_config.get("logs", "logs"))

            # 日志配置
            logging_config = self.config_manager.get_logging_config()
            self.log_level_combo.setCurrentText(logging_config.get("level", "INFO"))
            self.file_logging_checkbox.setChecked(
                logging_config.get("file_logging", True)
            )
            self.console_logging_checkbox.setChecked(
                logging_config.get("console_logging", True)
            )
            self.max_file_size_spin.setValue(
                logging_config.get("max_file_size", 10485760) // 1048576
            )
            self.backup_count_spin.setValue(logging_config.get("backup_count", 5))

            logger.info("配置加载完成")

        except Exception as e:
            logger.error(f"加载配置失败: {e}")

    def save_config(self) -> None:
        """保存配置"""
        try:
            # 应用配置
            app_config = {
                "language": self.language_combo.currentText(),
                "theme": self.theme_combo.currentText(),
                "window": {
                    "width": self.width_spin.value(),
                    "height": self.height_spin.value(),
                    "maximized": self.maximized_checkbox.isChecked(),
                },
            }
            self.config_manager.update_app_config(app_config)

            # UI配置
            ui_config = {
                "font_family": self.font_family_edit.text(),
                "font_size": self.font_size_spin.value(),
                "animation_enabled": self.animation_checkbox.isChecked(),
                "sound_enabled": self.sound_checkbox.isChecked(),
                "particle_effects": self.particle_checkbox.isChecked(),
            }
            self.config_manager.update_ui_config(ui_config)

            # 游戏配置
            game_config = {
                "physics_enabled": self.physics_checkbox.isChecked(),
                "gravity_strength": self.gravity_slider.value() / 100.0,
                "friction": self.friction_slider.value() / 100.0,
                "bounce_factor": self.bounce_slider.value() / 100.0,
                "collision_detection": self.collision_checkbox.isChecked(),
                "auto_save": self.auto_save_checkbox.isChecked(),
                "auto_save_interval": self.auto_save_interval_spin.value(),
            }
            self.config_manager.update_game_config(game_config)

            # 实验配置
            experiment_config = {
                "auto_progression": self.auto_progression_checkbox.isChecked(),
                "step_validation": self.step_validation_checkbox.isChecked(),
                "real_time_feedback": self.real_time_feedback_checkbox.isChecked(),
                "data_logging": self.data_logging_checkbox.isChecked(),
                "backup_enabled": self.backup_enabled_checkbox.isChecked(),
            }
            self.config_manager.update_experiment_config(experiment_config)

            # 路径配置
            paths_config = {
                "experiments": self.experiment_path_edit.text(),
                "templates": self.template_path_edit.text(),
                "backups": self.backup_path_edit.text(),
                "logs": self.log_path_edit.text(),
            }
            self.config_manager.set("paths", paths_config)

            # 日志配置
            logging_config = {
                "level": self.log_level_combo.currentText(),
                "file_logging": self.file_logging_checkbox.isChecked(),
                "console_logging": self.console_logging_checkbox.isChecked(),
                "max_file_size": self.max_file_size_spin.value() * 1048576,
                "backup_count": self.backup_count_spin.value(),
            }
            self.config_manager.set("logging", logging_config)

            # 保存配置
            self.config_manager.save_config()

            # 发送配置改变信号
            self.config_changed.emit(self.config_manager._config)

            logger.info("配置保存完成")

        except Exception as e:
            logger.error(f"保存配置失败: {e}")

    def reset_to_default(self) -> None:
        """重置为默认配置"""
        self.config_manager.reset_to_default()
        self.load_current_config()
        logger.info("配置已重置为默认值")

    def import_config(self) -> None:
        """导入配置"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "导入配置文件", "", "JSON文件 (*.json);;所有文件 (*)"
            )

            if file_path:
                try:
                    from .path_security import validate_dialog_path

                    file_path = str(validate_dialog_path(file_path))
                    with open(file_path, encoding="utf-8") as f:
                        import json

                        config_data = json.load(f)

                    # 验证配置数据
                    if not isinstance(config_data, dict):
                        QMessageBox.warning(self, "导入失败", "配置文件格式错误")
                        return

                    # 应用配置
                    self.config_manager.update_ui_config(config_data)

                    # 刷新界面
                    self.load_current_config()

                    QMessageBox.information(
                        self, "导入成功", f"配置文件已成功导入: {file_path}"
                    )
                    logger.info(f"配置文件导入成功: {file_path}")

                except json.JSONDecodeError:
                    QMessageBox.warning(self, "导入失败", "配置文件JSON格式错误")
                except Exception as e:
                    QMessageBox.warning(
                        self, "导入失败", f"导入配置文件时发生错误: {e}"
                    )
                    logger.error(f"导入配置文件失败: {e}")

        except Exception as e:
            logger.error(f"导入配置功能错误: {e}")
            QMessageBox.critical(self, "错误", f"导入配置功能发生错误: {e}")

    def export_config(self) -> None:
        """导出配置"""
        try:
            from datetime import datetime

            # 生成默认文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"VirtualChemLab_config_{timestamp}.json"

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出配置文件",
                default_filename,
                "JSON文件 (*.json);;所有文件 (*)",
            )

            if file_path:
                try:
                    from .path_security import validate_dialog_path

                    file_path = str(validate_dialog_path(file_path))
                    # 获取当前配置
                    config_data = self.config_manager.get_ui_config()

                    # 添加导出信息
                    export_data = {
                        "export_info": {
                            "export_time": datetime.now().isoformat(),
                            "version": "2.0",
                            "description": "VirtualChemLab配置文件",
                        },
                        "config": config_data,
                    }

                    with open(file_path, "w", encoding="utf-8") as f:
                        import json

                        json.dump(export_data, f, ensure_ascii=False, indent=2)

                    QMessageBox.information(
                        self, "导出成功", f"配置文件已成功导出: {file_path}"
                    )
                    logger.info(f"配置文件导出成功: {file_path}")

                except Exception as e:
                    QMessageBox.warning(
                        self, "导出失败", f"导出配置文件时发生错误: {e}"
                    )
                    logger.error(f"导出配置文件失败: {e}")

        except Exception as e:
            logger.error(f"导出配置功能错误: {e}")
            QMessageBox.critical(self, "错误", f"导出配置功能发生错误: {e}")

    def browse_folder(self, line_edit: QLineEdit) -> None:
        """浏览文件夹"""
        try:
            current_path = line_edit.text() or ""

            folder_path = QFileDialog.getExistingDirectory(
                self, "选择文件夹", current_path
            )

            if folder_path:
                try:
                    from .path_security import validate_dialog_path

                    folder_path = str(validate_dialog_path(folder_path))
                except ValueError:
                    QMessageBox.warning(self, "错误", "选择的目录不在允许的目录内")
                    return
                line_edit.setText(folder_path)
                logger.info(f"选择文件夹: {folder_path}")

        except Exception as e:
            logger.error(f"文件夹浏览功能错误: {e}")
            QMessageBox.critical(self, "错误", f"文件夹浏览功能发生错误: {e}")

    def apply_theme(self) -> None:
        """应用主题"""
        try:
            theme_name = self.config_manager.get("app.theme", "dark")

            # 应用主题样式
            if theme_name == "dark":
                self.setStyleSheet(
                    """
                    QDialog {
                        background-color: #1a1a2e;
                        color: #ffffff;
                    }
                    QGroupBox {
                        font-weight: bold;
                        border: 2px solid #4a90e2;
                        border-radius: 5px;
                        margin-top: 1ex;
                        padding-top: 10px;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        left: 10px;
                        padding: 0 5px 0 5px;
                    }
                    QTabWidget::pane {
                        border: 1px solid #4a90e2;
                        background-color: #16213e;
                    }
                    QTabBar::tab {
                        background-color: #2d1b69;
                        color: #ffffff;
                        padding: 8px 12px;
                        margin-right: 2px;
                    }
                    QTabBar::tab:selected {
                        background-color: #4a90e2;
                    }
                """
                )

            logger.info(f"主题应用成功: {theme_name}")

        except Exception as e:
            logger.warning(f"应用主题失败: {e}")

    def accept(self) -> None:
        """接受对话框"""
        self.save_config()
        super().accept()

    def get_config_summary(self) -> dict[str, Any]:
        """获取配置摘要"""
        return self.config_manager.get_config_summary()
