"""
设置对话框
用户偏好设置管理
"""

import json
import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..utils.i18n import I18n

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """设置对话框"""

    # 信号：设置已更改
    settings_changed = Signal(dict)

    def __init__(
        self,
        i18n_dir: str = "assets/i18n",
        settings_file: str = "config/settings.json",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.i18n = I18n(i18n_dir)
        self.settings_file = Path(settings_file)
        self.settings: dict[str, Any] = {}

        self.load_settings()
        self.init_ui()

    def init_ui(self) -> None:
        """初始化用户界面"""
        self.setWindowTitle(self.i18n.t("settings.title"))
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        # 选项卡
        tabs = QTabWidget()

        # 常规选项卡
        general_tab = self.create_general_tab()
        tabs.addTab(general_tab, self.i18n.t("settings.general"))

        # 外观选项卡
        appearance_tab = self.create_appearance_tab()
        tabs.addTab(appearance_tab, self.i18n.t("settings.appearance"))

        # 性能选项卡
        performance_tab = self.create_performance_tab()
        tabs.addTab(performance_tab, self.i18n.t("settings.performance"))

        # 高级选项卡
        advanced_tab = self.create_advanced_tab()
        tabs.addTab(advanced_tab, self.i18n.t("settings.advanced"))

        # 无障碍选项卡
        accessibility_tab = self.create_accessibility_tab()
        tabs.addTab(accessibility_tab, self.i18n.t("settings.accessibility"))

        layout.addWidget(tabs)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        reset_btn = QPushButton(self.i18n.t("settings.reset_defaults"))
        reset_btn.clicked.connect(self.on_reset_defaults)
        btn_layout.addWidget(reset_btn)

        import_btn = QPushButton(self.i18n.t("settings.import"))
        import_btn.clicked.connect(self.on_import_settings)
        btn_layout.addWidget(import_btn)

        export_btn = QPushButton(self.i18n.t("settings.export"))
        export_btn.clicked.connect(self.on_export_settings)
        btn_layout.addWidget(export_btn)

        cancel_btn = QPushButton(self.i18n.t("ui.cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton(self.i18n.t("settings.save"))
        save_btn.clicked.connect(self.on_save)
        save_btn.setDefault(True)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def create_general_tab(self) -> QWidget:
        """创建常规选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 语言设置
        lang_group = QGroupBox(self.i18n.t("settings.language"))
        lang_layout = QFormLayout(lang_group)

        self.language_combo = QComboBox()

        # 动态加载可用语言
        available_languages = self.i18n.get_available_languages()
        for lang_code in available_languages:
            lang_name = self.i18n.get_language_name(lang_code, native=True)
            self.language_combo.addItem(lang_name, lang_code)

        current_lang = self.settings.get("language", "zh_CN")
        index = self.language_combo.findData(current_lang)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)

        # 连接语言切换信号
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)

        lang_layout.addRow(
            self.i18n.t("settings.interface_language") + ":", self.language_combo
        )

        layout.addWidget(lang_group)

        # 启动设置
        startup_group = QGroupBox(self.i18n.t("settings.startup"))
        startup_layout = QVBoxLayout(startup_group)

        self.auto_load_last_cb = QCheckBox(
            self.i18n.t("settings.auto_load_last_experiment")
        )
        self.auto_load_last_cb.setChecked(
            self.settings.get("auto_load_last_experiment", False)
        )
        startup_layout.addWidget(self.auto_load_last_cb)

        self.show_welcome_cb = QCheckBox(self.i18n.t("settings.show_welcome_screen"))
        self.show_welcome_cb.setChecked(self.settings.get("show_welcome_screen", True))
        startup_layout.addWidget(self.show_welcome_cb)

        layout.addWidget(startup_group)

        layout.addStretch()
        return widget

    def create_appearance_tab(self) -> QWidget:
        """创建外观选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 主题设置
        theme_group = QGroupBox(self.i18n.t("settings.theme"))
        theme_layout = QFormLayout(theme_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem(self.i18n.t("settings.light_theme"), "light")
        self.theme_combo.addItem(self.i18n.t("settings.dark_theme"), "dark")
        self.theme_combo.addItem(self.i18n.t("settings.auto_theme"), "auto")

        current_theme = self.settings.get("theme", "light")
        index = self.theme_combo.findData(current_theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

        # 连接主题切换信号
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)

        theme_layout.addRow(
            self.i18n.t("settings.color_scheme") + ":", self.theme_combo
        )

        layout.addWidget(theme_group)

        # 字体设置
        font_group = QGroupBox(self.i18n.t("settings.font"))
        font_layout = QFormLayout(font_group)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(self.settings.get("font_size", 10))

        # 连接字体大小变化信号
        self.font_size_spin.valueChanged.connect(self.on_font_size_changed)

        font_layout.addRow(self.i18n.t("settings.font_size") + ":", self.font_size_spin)

        layout.addWidget(font_group)

        # 动画设置
        animation_group = QGroupBox(self.i18n.t("settings.animations"))
        animation_layout = QVBoxLayout(animation_group)

        self.enable_animations_cb = QCheckBox(self.i18n.t("settings.enable_animations"))
        self.enable_animations_cb.setChecked(
            self.settings.get("enable_animations", True)
        )

        # 连接动画设置变化信号
        self.enable_animations_cb.toggled.connect(self.on_animation_changed)

        animation_layout.addWidget(self.enable_animations_cb)

        layout.addWidget(animation_group)

        layout.addStretch()
        return widget

    def create_performance_tab(self) -> QWidget:
        """创建性能选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 渲染设置
        render_group = QGroupBox(self.i18n.t("settings.rendering"))
        render_layout = QFormLayout(render_group)

        self.quality_combo = QComboBox()
        self.quality_combo.addItem(self.i18n.t("settings.low_quality"), "low")
        self.quality_combo.addItem(self.i18n.t("settings.medium_quality"), "medium")
        self.quality_combo.addItem(self.i18n.t("settings.high_quality"), "high")

        current_quality = self.settings.get("render_quality", "medium")
        index = self.quality_combo.findData(current_quality)
        if index >= 0:
            self.quality_combo.setCurrentIndex(index)

        # 连接渲染质量变化信号
        self.quality_combo.currentIndexChanged.connect(self.on_render_quality_changed)

        render_layout.addRow(
            self.i18n.t("settings.graphics_quality") + ":", self.quality_combo
        )

        layout.addWidget(render_group)

        # 缓存设置
        cache_group = QGroupBox(self.i18n.t("settings.cache"))
        cache_layout = QFormLayout(cache_group)

        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(50, 1000)
        self.cache_size_spin.setSuffix(" MB")
        self.cache_size_spin.setValue(self.settings.get("cache_size_mb", 200))

        # 连接缓存大小变化信号
        self.cache_size_spin.valueChanged.connect(self.on_cache_size_changed)

        cache_layout.addRow(
            self.i18n.t("settings.cache_size") + ":", self.cache_size_spin
        )

        layout.addWidget(cache_group)

        # 自动保存
        autosave_group = QGroupBox(self.i18n.t("settings.auto_save"))
        autosave_layout = QFormLayout(autosave_group)

        self.autosave_cb = QCheckBox(self.i18n.t("settings.enable_auto_save"))
        self.autosave_cb.setChecked(self.settings.get("enable_auto_save", True))
        autosave_layout.addRow(self.autosave_cb)

        self.autosave_interval_spin = QSpinBox()
        self.autosave_interval_spin.setRange(1, 30)
        self.autosave_interval_spin.setSuffix(" " + self.i18n.t("settings.minutes"))
        self.autosave_interval_spin.setValue(
            self.settings.get("autosave_interval_min", 5)
        )
        self.autosave_interval_spin.setEnabled(self.autosave_cb.isChecked())
        self.autosave_cb.toggled.connect(self.autosave_interval_spin.setEnabled)

        autosave_layout.addRow(
            self.i18n.t("settings.save_interval") + ":", self.autosave_interval_spin
        )

        layout.addWidget(autosave_group)

        layout.addStretch()
        return widget

    def create_advanced_tab(self) -> QWidget:
        """创建高级选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 开发者选项
        dev_group = QGroupBox(self.i18n.t("settings.developer_options"))
        dev_layout = QVBoxLayout(dev_group)

        self.debug_mode_cb = QCheckBox(self.i18n.t("settings.enable_debug_mode"))
        self.debug_mode_cb.setChecked(self.settings.get("debug_mode", False))
        dev_layout.addWidget(self.debug_mode_cb)

        self.experimental_features_cb = QCheckBox(
            self.i18n.t("settings.enable_experimental_features")
        )
        self.experimental_features_cb.setChecked(
            self.settings.get("experimental_features", False)
        )
        dev_layout.addWidget(self.experimental_features_cb)

        self.verbose_logging_cb = QCheckBox(
            self.i18n.t("settings.enable_verbose_logging")
        )
        self.verbose_logging_cb.setChecked(self.settings.get("verbose_logging", False))
        dev_layout.addWidget(self.verbose_logging_cb)

        layout.addWidget(dev_group)

        # 数据管理
        data_group = QGroupBox(self.i18n.t("settings.data_management"))
        data_layout = QFormLayout(data_group)

        self.auto_backup_cb = QCheckBox(self.i18n.t("settings.enable_auto_backup"))
        self.auto_backup_cb.setChecked(self.settings.get("auto_backup", True))
        data_layout.addRow(self.auto_backup_cb)

        self.backup_frequency_spin = QSpinBox()
        self.backup_frequency_spin.setRange(1, 30)
        self.backup_frequency_spin.setSuffix(" " + self.i18n.t("settings.days"))
        self.backup_frequency_spin.setValue(
            self.settings.get("backup_frequency_days", 7)
        )
        self.backup_frequency_spin.setEnabled(self.auto_backup_cb.isChecked())
        self.auto_backup_cb.toggled.connect(self.backup_frequency_spin.setEnabled)
        data_layout.addRow(
            self.i18n.t("settings.backup_frequency") + ":", self.backup_frequency_spin
        )

        self.data_retention_spin = QSpinBox()
        self.data_retention_spin.setRange(30, 365)
        self.data_retention_spin.setSuffix(" " + self.i18n.t("settings.days"))
        self.data_retention_spin.setValue(self.settings.get("data_retention_days", 90))
        data_layout.addRow(
            self.i18n.t("settings.data_retention") + ":", self.data_retention_spin
        )

        layout.addWidget(data_group)

        # 网络设置
        network_group = QGroupBox(self.i18n.t("settings.network"))
        network_layout = QVBoxLayout(network_group)

        self.check_updates_cb = QCheckBox(
            self.i18n.t("settings.check_updates_automatically")
        )
        self.check_updates_cb.setChecked(self.settings.get("check_updates", True))
        network_layout.addWidget(self.check_updates_cb)

        self.analytics_cb = QCheckBox(self.i18n.t("settings.enable_analytics"))
        self.analytics_cb.setChecked(self.settings.get("enable_analytics", False))
        network_layout.addWidget(self.analytics_cb)

        layout.addWidget(network_group)

        layout.addStretch()
        return widget

    def create_accessibility_tab(self) -> QWidget:
        """创建无障碍选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 视觉辅助
        visual_group = QGroupBox(self.i18n.t("settings.visual_accessibility"))
        visual_layout = QVBoxLayout(visual_group)

        self.high_contrast_cb = QCheckBox(self.i18n.t("settings.enable_high_contrast"))
        self.high_contrast_cb.setChecked(self.settings.get("high_contrast", False))
        visual_layout.addWidget(self.high_contrast_cb)

        self.large_text_cb = QCheckBox(self.i18n.t("settings.enable_large_text"))
        self.large_text_cb.setChecked(self.settings.get("large_text", False))
        visual_layout.addWidget(self.large_text_cb)

        self.color_blind_support_cb = QCheckBox(
            self.i18n.t("settings.enable_color_blind_support")
        )
        self.color_blind_support_cb.setChecked(
            self.settings.get("color_blind_support", False)
        )
        visual_layout.addWidget(self.color_blind_support_cb)

        layout.addWidget(visual_group)

        # 交互辅助
        interaction_group = QGroupBox(self.i18n.t("settings.interaction_accessibility"))
        interaction_layout = QVBoxLayout(interaction_group)

        self.keyboard_navigation_cb = QCheckBox(
            self.i18n.t("settings.enable_keyboard_navigation")
        )
        self.keyboard_navigation_cb.setChecked(
            self.settings.get("keyboard_navigation", True)
        )
        interaction_layout.addWidget(self.keyboard_navigation_cb)

        self.screen_reader_cb = QCheckBox(
            self.i18n.t("settings.enable_screen_reader_support")
        )
        self.screen_reader_cb.setChecked(
            self.settings.get("screen_reader_support", False)
        )
        interaction_layout.addWidget(self.screen_reader_cb)

        self.focus_indicators_cb = QCheckBox(
            self.i18n.t("settings.enable_focus_indicators")
        )
        self.focus_indicators_cb.setChecked(self.settings.get("focus_indicators", True))
        interaction_layout.addWidget(self.focus_indicators_cb)

        layout.addWidget(interaction_group)

        # 通知设置
        notification_group = QGroupBox(self.i18n.t("settings.notifications"))
        notification_layout = QVBoxLayout(notification_group)

        self.experiment_complete_notifications_cb = QCheckBox(
            self.i18n.t("settings.experiment_complete_notifications")
        )
        self.experiment_complete_notifications_cb.setChecked(
            self.settings.get("experiment_complete_notifications", True)
        )
        notification_layout.addWidget(self.experiment_complete_notifications_cb)

        self.error_notifications_cb = QCheckBox(
            self.i18n.t("settings.error_notifications")
        )
        self.error_notifications_cb.setChecked(
            self.settings.get("error_notifications", True)
        )
        notification_layout.addWidget(self.error_notifications_cb)

        self.update_notifications_cb = QCheckBox(
            self.i18n.t("settings.update_notifications")
        )
        self.update_notifications_cb.setChecked(
            self.settings.get("update_notifications", True)
        )
        notification_layout.addWidget(self.update_notifications_cb)

        layout.addWidget(notification_group)

        layout.addStretch()
        return widget

    def load_settings(self) -> None:
        """加载设置"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, encoding="utf-8") as f:
                    self.settings = json.load(f)
            else:
                self.settings = self.get_default_settings()
        except Exception as e:
            logger.error(f"加载设置失败: {e}")
            self.settings = self.get_default_settings()

    def get_default_settings(self) -> dict[str, Any]:
        """获取默认设置"""
        return {
            # 常规设置
            "language": "zh_CN",
            "auto_load_last_experiment": False,
            "show_welcome_screen": True,
            # 外观设置
            "theme": "light",
            "font_size": 10,
            "enable_animations": True,
            # 性能设置
            "render_quality": "medium",
            "cache_size_mb": 200,
            "enable_auto_save": True,
            "autosave_interval_min": 5,
            # 高级设置
            "debug_mode": False,
            "experimental_features": False,
            "verbose_logging": False,
            "auto_backup": True,
            "backup_frequency_days": 7,
            "data_retention_days": 90,
            "check_updates": True,
            "enable_analytics": False,
            # 无障碍设置
            "high_contrast": False,
            "large_text": False,
            "color_blind_support": False,
            "keyboard_navigation": True,
            "screen_reader_support": False,
            "focus_indicators": True,
            # 通知设置
            "experiment_complete_notifications": True,
            "error_notifications": True,
            "update_notifications": True,
        }

    def collect_settings(self) -> dict[str, Any]:
        """收集当前设置"""
        settings = {
            # 常规设置
            "language": self.language_combo.currentData(),
            "auto_load_last_experiment": self.auto_load_last_cb.isChecked(),
            "show_welcome_screen": self.show_welcome_cb.isChecked(),
            # 外观设置
            "theme": self.theme_combo.currentData(),
            "font_size": self.font_size_spin.value(),
            "enable_animations": self.enable_animations_cb.isChecked(),
            # 性能设置
            "render_quality": self.quality_combo.currentData(),
            "cache_size_mb": self.cache_size_spin.value(),
            "enable_auto_save": self.autosave_cb.isChecked(),
            "autosave_interval_min": self.autosave_interval_spin.value(),
            # 高级设置
            "debug_mode": self.debug_mode_cb.isChecked(),
            "experimental_features": self.experimental_features_cb.isChecked(),
            "verbose_logging": self.verbose_logging_cb.isChecked(),
            "auto_backup": self.auto_backup_cb.isChecked(),
            "backup_frequency_days": self.backup_frequency_spin.value(),
            "data_retention_days": self.data_retention_spin.value(),
            "check_updates": self.check_updates_cb.isChecked(),
            "enable_analytics": self.analytics_cb.isChecked(),
            # 无障碍设置
            "high_contrast": self.high_contrast_cb.isChecked(),
            "large_text": self.large_text_cb.isChecked(),
            "color_blind_support": self.color_blind_support_cb.isChecked(),
            "keyboard_navigation": self.keyboard_navigation_cb.isChecked(),
            "screen_reader_support": self.screen_reader_cb.isChecked(),
            "focus_indicators": self.focus_indicators_cb.isChecked(),
            # 通知设置
            "experiment_complete_notifications": self.experiment_complete_notifications_cb.isChecked(),
            "error_notifications": self.error_notifications_cb.isChecked(),
            "update_notifications": self.update_notifications_cb.isChecked(),
        }

        # 验证设置
        if not self.validate_settings(settings):
            return {}

        return settings

    def validate_settings(self, settings: dict[str, Any]) -> bool:
        """验证设置"""
        try:
            # 验证字体大小
            if not (8 <= settings.get("font_size", 10) <= 24):
                QMessageBox.warning(
                    self, self.i18n.t("ui.warning"), "字体大小必须在8-24之间"
                )
                return False

            # 验证缓存大小
            if not (50 <= settings.get("cache_size_mb", 200) <= 1000):
                QMessageBox.warning(
                    self, self.i18n.t("ui.warning"), "缓存大小必须在50-1000MB之间"
                )
                return False

            # 验证自动保存间隔
            if not (1 <= settings.get("autosave_interval_min", 5) <= 30):
                QMessageBox.warning(
                    self, self.i18n.t("ui.warning"), "自动保存间隔必须在1-30分钟之间"
                )
                return False

            # 验证语言
            if not settings.get("language"):
                QMessageBox.warning(self, self.i18n.t("ui.warning"), "请选择有效的语言")
                return False

            # 验证主题
            if settings.get("theme") not in ["light", "dark", "auto"]:
                QMessageBox.warning(self, self.i18n.t("ui.warning"), "请选择有效的主题")
                return False

            # 验证渲染质量
            if settings.get("render_quality") not in ["low", "medium", "high"]:
                QMessageBox.warning(
                    self, self.i18n.t("ui.warning"), "请选择有效的渲染质量"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"设置验证失败: {e}")
            QMessageBox.critical(self, self.i18n.t("ui.error"), f"设置验证失败: {e}")
            return False

    def save_settings(self) -> bool:
        """保存设置"""
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            logger.info("设置已保存")
            return True
        except Exception as e:
            logger.error(f"保存设置失败: {e}")
            return False

    def on_save(self) -> None:
        """保存设置"""
        new_settings = self.collect_settings()

        # 如果验证失败，返回空字典
        if not new_settings:
            return

        # 检查是否有更改
        if new_settings != self.settings:
            self.settings = new_settings
            if self.save_settings():
                self.settings_changed.emit(self.settings)
                QMessageBox.information(
                    self,
                    self.i18n.t("ui.success"),
                    self.i18n.t("settings.save_success"),
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    self.i18n.t("error.title"),
                    self.i18n.t("settings.save_failed"),
                )
        else:
            self.accept()

    def on_language_changed(self, index: int) -> None:
        """语言切换时的实时预览"""
        if index < 0:
            return

        new_language = self.language_combo.itemData(index)
        if new_language and new_language != self.i18n.current_language:
            # 切换预览语言
            self.i18n.set_language(new_language)
            # 实时更新界面文本
            self.update_ui_texts()
            logger.info(f"语言预览切换到: {new_language}")

    def update_ui_texts(self) -> None:
        """更新界面文本"""
        self.setWindowTitle(self.i18n.t("settings.title"))

        # 更新选项卡标题
        tabs = self.findChild(QTabWidget)
        if tabs:
            tabs.setTabText(0, self.i18n.t("settings.general"))
            tabs.setTabText(1, self.i18n.t("settings.appearance"))
            tabs.setTabText(2, self.i18n.t("settings.performance"))

        # 更新按钮文本
        for btn in self.findChildren(QPushButton):
            if btn.text() == "恢复默认":
                btn.setText(self.i18n.t("settings.reset_defaults"))
            elif btn.text() == "取消":
                btn.setText(self.i18n.t("ui.cancel"))
            elif btn.text() == "保存":
                btn.setText(self.i18n.t("settings.save"))

    def on_reset_defaults(self) -> None:
        """重置为默认设置"""
        reply = QMessageBox.question(
            self,
            self.i18n.t("settings.reset_confirm_title"),
            self.i18n.t("settings.reset_confirm_message"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.settings = self.get_default_settings()
            self.save_settings()
            self.settings_changed.emit(self.settings)
            QMessageBox.information(
                self, self.i18n.t("ui.success"), self.i18n.t("settings.reset_success")
            )
            self.accept()

    def on_import_settings(self) -> None:
        """导入设置"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                self.i18n.t("settings.import_title"),
                "",
                "JSON Files (*.json);;All Files (*)",
            )

            if file_path:
                with open(file_path, encoding="utf-8") as f:
                    imported_settings = json.load(f)

                # 验证导入的设置
                if self.validate_imported_settings(imported_settings):
                    self.settings.update(imported_settings)
                    self.load_settings_to_ui()
                    QMessageBox.information(
                        self,
                        self.i18n.t("ui.success"),
                        self.i18n.t("settings.import_success"),
                    )
                else:
                    QMessageBox.warning(
                        self,
                        self.i18n.t("ui.warning"),
                        self.i18n.t("settings.import_invalid"),
                    )

        except Exception as e:
            logger.error(f"导入设置失败: {e}")
            QMessageBox.critical(self, self.i18n.t("error.title"), f"导入设置失败: {e}")

    def on_export_settings(self) -> None:
        """导出设置"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                self.i18n.t("settings.export_title"),
                "settings_backup.json",
                "JSON Files (*.json);;All Files (*)",
            )

            if file_path:
                current_settings = self.collect_settings()
                if current_settings:
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(current_settings, f, indent=2, ensure_ascii=False)

                    QMessageBox.information(
                        self,
                        self.i18n.t("ui.success"),
                        self.i18n.t("settings.export_success"),
                    )
                else:
                    QMessageBox.warning(
                        self,
                        self.i18n.t("ui.warning"),
                        self.i18n.t("settings.export_failed"),
                    )

        except Exception as e:
            logger.error(f"导出设置失败: {e}")
            QMessageBox.critical(self, self.i18n.t("error.title"), f"导出设置失败: {e}")

    def validate_imported_settings(self, settings: dict[str, Any]) -> bool:
        """验证导入的设置"""
        try:
            # 检查必需字段
            required_fields = ["language", "theme", "font_size"]
            for field in required_fields:
                if field not in settings:
                    return False

            # 验证字段值
            if not (8 <= settings.get("font_size", 10) <= 24):
                return False

            if settings.get("theme") not in ["light", "dark", "auto"]:
                return False

            return settings.get("language") in ["zh_CN", "en_US"]

        except Exception as e:
            logger.error(f"验证导入设置失败: {e}")
            return False

    def load_settings_to_ui(self) -> None:
        """将设置加载到UI"""
        try:
            # 常规设置
            current_lang = self.settings.get("language", "zh_CN")
            index = self.language_combo.findData(current_lang)
            if index >= 0:
                self.language_combo.setCurrentIndex(index)

            self.auto_load_last_cb.setChecked(
                self.settings.get("auto_load_last_experiment", False)
            )
            self.show_welcome_cb.setChecked(
                self.settings.get("show_welcome_screen", True)
            )

            # 外观设置
            current_theme = self.settings.get("theme", "light")
            index = self.theme_combo.findData(current_theme)
            if index >= 0:
                self.theme_combo.setCurrentIndex(index)

            self.font_size_spin.setValue(self.settings.get("font_size", 10))
            self.enable_animations_cb.setChecked(
                self.settings.get("enable_animations", True)
            )

            # 性能设置
            current_quality = self.settings.get("render_quality", "medium")
            index = self.quality_combo.findData(current_quality)
            if index >= 0:
                self.quality_combo.setCurrentIndex(index)

            self.cache_size_spin.setValue(self.settings.get("cache_size_mb", 200))
            self.autosave_cb.setChecked(self.settings.get("enable_auto_save", True))
            self.autosave_interval_spin.setValue(
                self.settings.get("autosave_interval_min", 5)
            )

            # 高级设置
            self.debug_mode_cb.setChecked(self.settings.get("debug_mode", False))
            self.experimental_features_cb.setChecked(
                self.settings.get("experimental_features", False)
            )
            self.verbose_logging_cb.setChecked(
                self.settings.get("verbose_logging", False)
            )
            self.auto_backup_cb.setChecked(self.settings.get("auto_backup", True))
            self.backup_frequency_spin.setValue(
                self.settings.get("backup_frequency_days", 7)
            )
            self.data_retention_spin.setValue(
                self.settings.get("data_retention_days", 90)
            )
            self.check_updates_cb.setChecked(self.settings.get("check_updates", True))
            self.analytics_cb.setChecked(self.settings.get("enable_analytics", False))

            # 无障碍设置
            self.high_contrast_cb.setChecked(self.settings.get("high_contrast", False))
            self.large_text_cb.setChecked(self.settings.get("large_text", False))
            self.color_blind_support_cb.setChecked(
                self.settings.get("color_blind_support", False)
            )
            self.keyboard_navigation_cb.setChecked(
                self.settings.get("keyboard_navigation", True)
            )
            self.screen_reader_cb.setChecked(
                self.settings.get("screen_reader_support", False)
            )
            self.focus_indicators_cb.setChecked(
                self.settings.get("focus_indicators", True)
            )

            # 通知设置
            self.experiment_complete_notifications_cb.setChecked(
                self.settings.get("experiment_complete_notifications", True)
            )
            self.error_notifications_cb.setChecked(
                self.settings.get("error_notifications", True)
            )
            self.update_notifications_cb.setChecked(
                self.settings.get("update_notifications", True)
            )

        except Exception as e:
            logger.error(f"加载设置到UI失败: {e}")

    def on_theme_changed(self, index: int) -> None:
        """主题切换处理"""
        if index < 0:
            return

        theme = self.theme_combo.itemData(index)
        if theme:
            logger.info(f"主题预览切换到: {theme}")
            # 发送主题预览信号
            self.settings_changed.emit({"theme_preview": theme})

    def on_font_size_changed(self, value: int) -> None:
        """字体大小变化处理"""
        logger.info(f"字体大小预览: {value}")
        # 发送字体大小预览信号
        self.settings_changed.emit({"font_size_preview": value})

    def on_animation_changed(self, enabled: bool) -> None:
        """动画设置变化处理"""
        logger.info(f"动画设置预览: {enabled}")
        # 发送动画设置预览信号
        self.settings_changed.emit({"animations_preview": enabled})

    def on_render_quality_changed(self, index: int) -> None:
        """渲染质量变化处理"""
        if index < 0:
            return

        quality = self.quality_combo.itemData(index)
        if quality:
            logger.info(f"渲染质量预览: {quality}")
            # 发送渲染质量预览信号
            self.settings_changed.emit({"render_quality_preview": quality})

    def on_cache_size_changed(self, value: int) -> None:
        """缓存大小变化处理"""
        logger.info(f"缓存大小预览: {value} MB")
        # 发送缓存大小预览信号
        self.settings_changed.emit({"cache_size_preview": value})
