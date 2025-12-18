"""
系统维护工具 - GUI界面

提供友好的图形界面进行缓存清理和错误修复
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from PySide6.QtCore import QSize, Qt, QThread, Signal
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QDialog,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QProgressBar,
        QPushButton,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    HAS_QT = True
except ImportError:
    HAS_QT = False
    print("警告: 未安装PySide6，GUI功能不可用")

from src.contracts.maintenance_service import (
    CacheType,
    CleanupRequest,
    DiagnosisRequest,
    FixRequest,
)
from src.core.maintenance import MaintenanceServiceImpl


class MaintenanceWorker(QThread):
    """维护任务工作线程"""

    finished = Signal(object)  # 完成信号
    progress = Signal(str)  # 进度信号
    error = Signal(str)  # 错误信号

    def __init__(self, service: MaintenanceServiceImpl, task_type: str, **kwargs):
        super().__init__()
        self.service = service
        self.task_type = task_type
        self.kwargs = kwargs

    def run(self):
        """执行任务"""
        try:
            if self.task_type == "cleanup_cache":
                self.progress.emit("正在清理缓存...")
                result = self.service.cleanup_cache(self.kwargs.get("request"))
                self.finished.emit(result)

            elif self.task_type == "diagnose":
                self.progress.emit("正在诊断系统...")
                result = self.service.diagnose_system(self.kwargs.get("request"))
                self.finished.emit(result)

            elif self.task_type == "fix_issues":
                self.progress.emit("正在修复问题...")
                result = self.service.fix_issues(self.kwargs.get("request"))
                self.finished.emit(result)

            elif self.task_type == "health_check":
                self.progress.emit("正在检查健康状态...")
                result = self.service.check_health()
                self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))


class MaintenanceDialog(QDialog):
    """系统维护对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统维护工具")
        self.setMinimumSize(QSize(800, 600))

        # 初始化服务
        self.service = MaintenanceServiceImpl()
        self.current_worker = None

        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 标题
        title_label = QLabel("🔧 VirtualChemLab 系统维护工具")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 选项卡
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_cache_tab(), "缓存清理")
        self.tabs.addTab(self.create_diagnosis_tab(), "错误诊断")
        self.tabs.addTab(self.create_health_tab(), "健康检查")
        layout.addWidget(self.tabs)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)

        # 结果文本框
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(200)
        layout.addWidget(self.result_text)

        # 按钮
        button_layout = QHBoxLayout()
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)

    def create_cache_tab(self) -> QWidget:
        """创建缓存清理选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 缓存信息组
        info_group = QGroupBox("缓存信息")
        info_layout = QVBoxLayout(info_group)

        self.cache_info_btn = QPushButton("获取缓存信息")
        self.cache_info_btn.clicked.connect(self.get_cache_info)
        info_layout.addWidget(self.cache_info_btn)

        self.cache_info_label = QLabel("点击按钮获取缓存信息")
        info_layout.addWidget(self.cache_info_label)

        layout.addWidget(info_group)

        # 清理选项组
        options_group = QGroupBox("清理选项")
        options_layout = QVBoxLayout(options_group)

        self.cache_type_checks = {}
        for cache_type in [CacheType.MEMORY, CacheType.DISK, CacheType.REDIS, CacheType.TEMPLATE, CacheType.ALL]:
            checkbox = QCheckBox(cache_type.value.upper())
            checkbox.setChecked(cache_type == CacheType.ALL)
            self.cache_type_checks[cache_type] = checkbox
            options_layout.addWidget(checkbox)

        self.expired_only_check = QCheckBox("仅清理过期缓存")
        options_layout.addWidget(self.expired_only_check)

        layout.addWidget(options_group)

        # 清理按钮
        self.cleanup_btn = QPushButton("开始清理")
        self.cleanup_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }")
        self.cleanup_btn.clicked.connect(self.cleanup_cache)
        layout.addWidget(self.cleanup_btn)

        layout.addStretch()
        return widget

    def create_diagnosis_tab(self) -> QWidget:
        """创建错误诊断选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 诊断按钮
        self.diagnose_btn = QPushButton("开始诊断")
        self.diagnose_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 10px; }")
        self.diagnose_btn.clicked.connect(self.diagnose_system)
        layout.addWidget(self.diagnose_btn)

        # 问题列表
        issues_group = QGroupBox("发现的问题")
        issues_layout = QVBoxLayout(issues_group)

        self.issues_list = QListWidget()
        issues_layout.addWidget(self.issues_list)

        layout.addWidget(issues_group)

        # 修复按钮
        fix_layout = QHBoxLayout()
        self.fix_selected_btn = QPushButton("修复选中问题")
        self.fix_selected_btn.clicked.connect(self.fix_selected_issues)
        self.fix_selected_btn.setEnabled(False)
        fix_layout.addWidget(self.fix_selected_btn)

        self.fix_all_btn = QPushButton("修复所有可修复问题")
        self.fix_all_btn.clicked.connect(self.fix_all_issues)
        self.fix_all_btn.setEnabled(False)
        fix_layout.addWidget(self.fix_all_btn)

        layout.addLayout(fix_layout)

        layout.addStretch()
        return widget

    def create_health_tab(self) -> QWidget:
        """创建健康检查选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 健康检查按钮
        self.health_check_btn = QPushButton("检查系统健康")
        self.health_check_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; padding: 10px; }")
        self.health_check_btn.clicked.connect(self.check_health)
        layout.addWidget(self.health_check_btn)

        # 健康信息
        health_group = QGroupBox("健康状态")
        health_layout = QVBoxLayout(health_group)

        self.health_score_label = QLabel("健康评分: --")
        self.health_score_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        health_layout.addWidget(self.health_score_label)

        self.health_status_label = QLabel("状态: --")
        health_layout.addWidget(self.health_status_label)

        self.health_details_text = QTextEdit()
        self.health_details_text.setReadOnly(True)
        health_layout.addWidget(self.health_details_text)

        layout.addWidget(health_group)

        layout.addStretch()
        return widget

    def get_cache_info(self):
        """获取缓存信息"""
        try:
            cache_infos = self.service.get_cache_info()

            if not cache_infos:
                self.cache_info_label.setText("没有缓存信息")
                return

            info_text = "缓存信息:\n"
            total_size = 0
            total_items = 0

            for info in cache_infos:
                size_mb = info.size_bytes / (1024 * 1024)
                info_text += f"\n{info.cache_type.value.upper()}:\n"
                info_text += f"  项目数: {info.item_count}\n"
                info_text += f"  大小: {size_mb:.2f} MB\n"
                info_text += f"  过期项: {info.expired_count}\n"

                total_size += info.size_bytes
                total_items += info.item_count

            total_size_mb = total_size / (1024 * 1024)
            info_text += f"\n总计: {total_items}项, {total_size_mb:.2f} MB"

            self.cache_info_label.setText(info_text)

        except Exception as e:
            self.show_error(f"获取缓存信息失败: {e}")

    def cleanup_cache(self):
        """清理缓存"""
        # 获取选中的缓存类型
        cache_types = [ct for ct, checkbox in self.cache_type_checks.items() if checkbox.isChecked()]

        if not cache_types:
            self.show_error("请至少选择一种缓存类型")
            return

        request = CleanupRequest(
            cache_types=cache_types,
            include_expired_only=self.expired_only_check.isChecked(),
        )

        self.run_task("cleanup_cache", request=request)

    def diagnose_system(self):
        """诊断系统"""
        request = DiagnosisRequest()
        self.run_task("diagnose", request=request)

    def fix_selected_issues(self):
        """修复选中的问题"""
        selected_items = self.issues_list.selectedItems()
        if not selected_items:
            self.show_error("请选择要修复的问题")
            return

        issue_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]

        request = FixRequest(issue_ids=issue_ids)
        self.run_task("fix_issues", request=request)

    def fix_all_issues(self):
        """修复所有问题"""
        request = FixRequest(fix_all=True)
        self.run_task("fix_issues", request=request)

    def check_health(self):
        """检查健康"""
        self.run_task("health_check")

    def run_task(self, task_type: str, **kwargs):
        """运行任务"""
        # 禁用按钮
        self.set_buttons_enabled(False)

        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度

        # 创建工作线程
        self.current_worker = MaintenanceWorker(self.service, task_type, **kwargs)
        self.current_worker.finished.connect(self.on_task_finished)
        self.current_worker.progress.connect(self.on_task_progress)
        self.current_worker.error.connect(self.on_task_error)
        self.current_worker.start()

    def on_task_finished(self, result):
        """任务完成"""
        self.progress_bar.setVisible(False)
        self.set_buttons_enabled(True)

        # 根据任务类型显示结果
        if hasattr(result, "__class__"):
            class_name = result.__class__.__name__

            if class_name == "CleanupResponse":
                self.show_cleanup_result(result)
            elif class_name == "DiagnosisResponse":
                self.show_diagnosis_result(result)
            elif class_name == "FixResponse":
                self.show_fix_result(result)
            elif class_name == "HealthCheckResponse":
                self.show_health_result(result)

    def on_task_progress(self, message: str):
        """任务进度"""
        self.status_label.setText(message)

    def on_task_error(self, error: str):
        """任务错误"""
        self.progress_bar.setVisible(False)
        self.set_buttons_enabled(True)
        self.show_error(error)

    def show_cleanup_result(self, result):
        """显示清理结果"""
        if result.success:
            text = "✅ 清理成功!\n\n"
            text += f"清理项目数: {result.total_items_cleaned}\n"
            text += f"释放空间: {result.total_bytes_freed / (1024*1024):.2f} MB\n"
            text += f"耗时: {result.duration_seconds:.2f} 秒\n"
            self.result_text.setStyleSheet("color: green;")
        else:
            text = f"❌ 清理失败\n\n{result.message}\n"
            if result.errors:
                text += "\n错误:\n" + "\n".join(result.errors)
            self.result_text.setStyleSheet("color: red;")

        self.result_text.setText(text)
        self.status_label.setText("清理完成")

        # 刷新缓存信息
        self.get_cache_info()

    def show_diagnosis_result(self, result):
        """显示诊断结果"""
        self.issues_list.clear()

        if result.success:
            text = "✅ 诊断完成\n\n"
            text += f"发现问题: {len(result.issues)}个\n"
            text += f"可修复: {result.fixable_count}个\n"
            text += f"严重问题: {result.critical_count}个\n"
            text += f"健康评分: {result.health_score:.1f}/100\n"

            # 填充问题列表
            for issue in result.issues:
                severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "ℹ️"}

                item_text = f"{severity_icon.get(issue.severity.value, '•')} [{issue.severity.value.upper()}] {issue.title}"
                if issue.fix_available:
                    item_text += " ✓"

                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, issue.issue_id)
                self.issues_list.addItem(item)

            # 启用修复按钮
            self.fix_selected_btn.setEnabled(result.fixable_count > 0)
            self.fix_all_btn.setEnabled(result.fixable_count > 0)

            self.result_text.setStyleSheet("color: green;")
        else:
            text = f"❌ 诊断失败\n\n{result.message}"
            self.result_text.setStyleSheet("color: red;")

        self.result_text.setText(text)
        self.status_label.setText("诊断完成")

    def show_fix_result(self, result):
        """显示修复结果"""
        if result.success:
            text = "✅ 修复成功!\n\n"
            text += f"成功修复: {result.total_fixed}个\n"
            text += f"修复失败: {result.total_failed}个\n"
            self.result_text.setStyleSheet("color: green;")

            # 重新诊断
            self.diagnose_system()
        else:
            text = f"❌ 修复失败\n\n{result.message}\n"
            if result.errors:
                text += "\n错误:\n" + "\n".join(result.errors)
            self.result_text.setStyleSheet("color: red;")

        self.result_text.setText(text)
        self.status_label.setText("修复完成")

    def show_health_result(self, result):
        """显示健康检查结果"""
        # 健康评分
        score_color = "green" if result.health_score >= 80 else "orange" if result.health_score >= 60 else "red"
        self.health_score_label.setText(f"健康评分: {result.health_score:.1f}/100")
        self.health_score_label.setStyleSheet(f"color: {score_color};")

        # 健康状态
        status_text = "✅ 健康" if result.healthy else "⚠️ 需要注意"
        self.health_status_label.setText(f"状态: {status_text}")

        # 详细信息
        details = "缓存状态:\n"
        details += f"  总大小: {result.cache_status.get('total_size', 0) / (1024*1024):.2f} MB\n"
        details += f"  总项目数: {result.cache_status.get('total_items', 0)}\n"
        details += f"  过期项: {result.cache_status.get('expired_items', 0)}\n\n"

        details += "错误状态:\n"
        details += f"  总问题数: {result.error_status.get('total_issues', 0)}\n"
        details += f"  严重问题: {result.error_status.get('critical_issues', 0)}\n"
        details += f"  高优先级问题: {result.error_status.get('high_issues', 0)}\n"
        details += f"  可修复问题: {result.error_status.get('fixable_issues', 0)}\n\n"

        if result.recommendations:
            details += "建议:\n"
            for rec in result.recommendations:
                details += f"  • {rec}\n"

        self.health_details_text.setText(details)
        self.status_label.setText("健康检查完成")

        # 结果文本
        text = f"{'✅' if result.healthy else '⚠️'} 健康检查完成\n\n"
        text += f"健康评分: {result.health_score:.1f}/100"
        self.result_text.setText(text)

    def show_error(self, message: str):
        """显示错误"""
        self.result_text.setStyleSheet("color: red;")
        self.result_text.setText(f"❌ 错误:\n\n{message}")
        self.status_label.setText("错误")

    def set_buttons_enabled(self, enabled: bool):
        """设置按钮启用状态"""
        self.cleanup_btn.setEnabled(enabled)
        self.diagnose_btn.setEnabled(enabled)
        self.fix_selected_btn.setEnabled(enabled)
        self.fix_all_btn.setEnabled(enabled)
        self.health_check_btn.setEnabled(enabled)
        self.cache_info_btn.setEnabled(enabled)


def main():
    """主函数"""
    if not HAS_QT:
        print("错误: 需要安装PySide6才能运行GUI工具")
        print("请运行: pip install PySide6")
        return

    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用Fusion风格

    dialog = MaintenanceDialog()
    dialog.exec()


if __name__ == "__main__":
    main()
