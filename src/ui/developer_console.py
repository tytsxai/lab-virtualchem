"""
开发者控制台
提供开发调试工具和系统监控功能
"""

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.dev_auth import DeveloperAuth
from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class LogViewerWidget(QWidget):
    """日志查看器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.log_file_path = "logs/app.log"
        self.auto_refresh = False

        # 定时刷新
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_logs)

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 控制栏
        control_layout = QHBoxLayout()

        # 日志级别过滤
        control_layout.addWidget(QLabel("日志级别:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.currentTextChanged.connect(self.filter_logs)
        control_layout.addWidget(self.level_combo)

        # 搜索
        control_layout.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词...")
        self.search_input.textChanged.connect(self.filter_logs)
        control_layout.addWidget(self.search_input)

        # 自动刷新
        self.auto_refresh_cb = QCheckBox("自动刷新")
        self.auto_refresh_cb.stateChanged.connect(self.toggle_auto_refresh)
        control_layout.addWidget(self.auto_refresh_cb)

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_logs)
        control_layout.addWidget(refresh_btn)

        # 清空按钮
        clear_btn = QPushButton("清空显示")
        clear_btn.clicked.connect(self.clear_display)
        control_layout.addWidget(clear_btn)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # 日志显示区
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_display)

        # 加载日志
        self.load_logs()

    def load_logs(self):
        """加载日志文件"""
        try:
            if Path(self.log_file_path).exists():
                with open(self.log_file_path, encoding="utf-8") as f:
                    # 读取最后1000行
                    lines = f.readlines()[-1000:]
                    self.all_logs = "".join(lines)
                    self.filter_logs()
            else:
                self.log_display.setText(f"日志文件不存在: {self.log_file_path}")
        except Exception as e:
            self.log_display.setText(f"加载日志失败: {e}")

    def filter_logs(self):
        """过滤日志"""
        level = self.level_combo.currentText()
        search_text = self.search_input.text().lower()

        if not hasattr(self, "all_logs"):
            return

        lines = self.all_logs.split("\n")
        filtered_lines = []

        for line in lines:
            # 级别过滤
            if level != "ALL" and f"[{level}]" not in line:
                continue

            # 关键词过滤
            if search_text and search_text not in line.lower():
                continue

            filtered_lines.append(line)

        self.log_display.setText("\n".join(filtered_lines))

        # 滚动到底部
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_display.setTextCursor(cursor)

    def toggle_auto_refresh(self, state):
        """切换自动刷新"""
        if state == Qt.Checked:
            self.refresh_timer.start(2000)  # 每2秒刷新
        else:
            self.refresh_timer.stop()

    def clear_display(self):
        """清空显示"""
        self.log_display.clear()


class PerformanceMonitorWidget(QWidget):
    """性能监控器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

        # 定时更新
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_metrics)
        self.update_timer.start(1000)  # 每秒更新

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 系统指标
        system_group = QGroupBox("系统指标")
        system_layout = QVBoxLayout()

        self.cpu_label = QLabel("CPU使用率: --")
        self.memory_label = QLabel("内存使用: --")
        self.thread_label = QLabel("线程数: --")

        system_layout.addWidget(self.cpu_label)
        system_layout.addWidget(self.memory_label)
        system_layout.addWidget(self.thread_label)
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)

        # 应用指标
        app_group = QGroupBox("应用指标")
        app_layout = QVBoxLayout()

        self.request_label = QLabel("请求数: 0")
        self.error_label = QLabel("错误数: 0")
        self.avg_response_label = QLabel("平均响应时间: -- ms")

        app_layout.addWidget(self.request_label)
        app_layout.addWidget(self.error_label)
        app_layout.addWidget(self.avg_response_label)
        app_group.setLayout(app_layout)
        layout.addWidget(app_group)

        layout.addStretch()

    def update_metrics(self):
        """更新性能指标"""
        try:
            import psutil

            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.cpu_label.setText(f"CPU使用率: {cpu_percent:.1f}%")

            # 内存
            memory = psutil.virtual_memory()
            memory_mb = memory.used / (1024 * 1024)
            memory_percent = memory.percent
            self.memory_label.setText(f"内存使用: {memory_mb:.0f} MB ({memory_percent:.1f}%)")

            # 线程
            process = psutil.Process()
            thread_count = process.num_threads()
            self.thread_label.setText(f"线程数: {thread_count}")

        except ImportError:
            self.cpu_label.setText("CPU使用率: 需安装psutil")
            self.memory_label.setText("内存使用: 需安装psutil")
            self.update_timer.stop()
        except Exception as e:
            logger.error(f"更新性能指标失败: {e}")


class ConfigEditorWidget(QWidget):
    """配置编辑器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = Config()
        self.init_ui()
        self.load_config()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 工具栏
        toolbar = QHBoxLayout()

        reload_btn = QPushButton("重新加载")
        reload_btn.clicked.connect(self.load_config)
        toolbar.addWidget(reload_btn)

        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self.save_config)
        toolbar.addWidget(save_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 配置树
        self.config_tree = QTreeWidget()
        self.config_tree.setHeaderLabels(["配置项", "值"])
        self.config_tree.setColumnWidth(0, 300)
        layout.addWidget(self.config_tree)

        # JSON编辑器
        json_group = QGroupBox("JSON编辑器")
        json_layout = QVBoxLayout()

        self.json_editor = QTextEdit()
        self.json_editor.setFont(QFont("Consolas", 10))
        json_layout.addWidget(self.json_editor)

        json_group.setLayout(json_layout)
        layout.addWidget(json_group)

    def load_config(self):
        """加载配置"""
        try:
            config_dict = self.config.config

            # 更新树视图
            self.config_tree.clear()
            self._build_tree(config_dict, self.config_tree.invisibleRootItem())
            self.config_tree.expandAll()

            # 更新JSON编辑器
            json_str = json.dumps(config_dict, indent=4, ensure_ascii=False)
            self.json_editor.setText(json_str)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载配置失败: {e}")

    def _build_tree(self, data: Any, parent: QTreeWidgetItem):
        """构建配置树"""
        if isinstance(data, dict):
            for key, value in data.items():
                item = QTreeWidgetItem(parent, [str(key), ""])
                if isinstance(value, (dict, list)):
                    self._build_tree(value, item)
                else:
                    item.setText(1, str(value))
        elif isinstance(data, list):
            for i, value in enumerate(data):
                item = QTreeWidgetItem(parent, [f"[{i}]", ""])
                if isinstance(value, (dict, list)):
                    self._build_tree(value, item)
                else:
                    item.setText(1, str(value))

    def save_config(self):
        """保存配置"""
        try:
            # 从JSON编辑器解析
            json_str = self.json_editor.toPlainText()
            new_config = json.loads(json_str)

            # 保存到文件
            with open(self.config.config_file, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=4, ensure_ascii=False)

            QMessageBox.information(self, "成功", "配置已保存，部分配置需要重启应用后生效")

            # 重新加载
            self.config.reload()
            self.load_config()

        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "错误", f"JSON格式错误: {e}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {e}")


class DeveloperConsole(QMainWindow):
    """开发者控制台主窗口"""

    closed = Signal()  # 窗口关闭信号

    def __init__(self, dev_auth: DeveloperAuth, parent=None):
        super().__init__(parent)
        if dev_auth is None or not dev_auth.is_authenticated():
            raise PermissionError("Developer console requires an authenticated developer session")
        self.dev_auth = dev_auth
        self.init_ui()

        logger.info("开发者控制台已启动")

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("VirtualChemLab - 开发者控制台")
        self.resize(1200, 800)

        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # 标题栏
        header = QHBoxLayout()
        title_label = QLabel("🛠️ 开发者控制台")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")
        header.addWidget(title_label)

        # 会话信息
        session = self.dev_auth.get_session()
        if session:
            session_label = QLabel(
                f"会话ID: {session.session_id[:8]}... | "
                f"过期时间: {session.expires_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            session_label.setStyleSheet("color: #666; font-size: 11px;")
            header.addWidget(session_label)

        header.addStretch()

        # 关闭按钮
        close_btn = QPushButton("关闭控制台")
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)

        layout.addLayout(header)

        # 标签页
        self.tab_widget = QTabWidget()

        # 日志查看器
        if self.dev_auth.has_feature("log_viewer"):
            self.log_viewer = LogViewerWidget()
            self.tab_widget.addTab(self.log_viewer, "📋 日志查看")

        # 性能监控
        if self.dev_auth.has_feature("performance_monitor"):
            self.perf_monitor = PerformanceMonitorWidget()
            self.tab_widget.addTab(self.perf_monitor, "📊 性能监控")

        # 配置编辑器
        if self.dev_auth.has_feature("config_editor"):
            self.config_editor = ConfigEditorWidget()
            self.tab_widget.addTab(self.config_editor, "⚙️ 配置编辑")

        # 调试控制台
        if self.dev_auth.has_feature("debug_console"):
            self.debug_console = self._create_debug_console()
            self.tab_widget.addTab(self.debug_console, "🐛 调试控制台")

        # 数据库查看器（如果启用）
        if self.dev_auth.has_feature("database_viewer"):
            self.db_viewer = self._create_database_viewer()
            self.tab_widget.addTab(self.db_viewer, "💾 数据库")

        # API测试器（如果启用）
        if self.dev_auth.has_feature("api_tester"):
            self.api_tester = self._create_api_tester()
            self.tab_widget.addTab(self.api_tester, "🌐 API测试")

        layout.addWidget(self.tab_widget)

        # 状态栏
        self.statusBar().showMessage("开发者模式已激活")

    def _create_debug_console(self) -> QWidget:
        """创建调试控制台"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 命令输入
        cmd_layout = QHBoxLayout()
        cmd_layout.addWidget(QLabel("Python命令:"))

        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("输入Python代码...")
        self.cmd_input.returnPressed.connect(self._execute_command)
        cmd_layout.addWidget(self.cmd_input)

        exec_btn = QPushButton("执行")
        exec_btn.clicked.connect(self._execute_command)
        cmd_layout.addWidget(exec_btn)

        layout.addLayout(cmd_layout)

        # 输出显示
        self.cmd_output = QTextEdit()
        self.cmd_output.setReadOnly(True)
        self.cmd_output.setFont(QFont("Consolas", 9))
        layout.addWidget(self.cmd_output)

        # 警告标签
        warning = QLabel("⚠️ 警告: 此功能可以执行任意Python代码，请谨慎使用！")
        warning.setStyleSheet("color: red; padding: 5px; background-color: #fff3cd;")
        layout.addWidget(warning)

        return widget

    def _execute_command(self):
        """执行Python命令"""
        command = self.cmd_input.text().strip()
        if not command:
            return

        self.cmd_output.append(f"\n>>> {command}")

        try:
            # 创建执行环境
            import sys
            from io import StringIO

            # 捕获输出
            old_stdout = sys.stdout
            sys.stdout = output_buffer = StringIO()

            # 执行命令
            result = eval(command)

            # 恢复输出
            sys.stdout = old_stdout
            output = output_buffer.getvalue()

            if output:
                self.cmd_output.append(output)
            if result is not None:
                self.cmd_output.append(str(result))

        except SyntaxError:
            # 尝试作为语句执行
            try:
                exec(command)
                sys.stdout = old_stdout
                output = output_buffer.getvalue()
                if output:
                    self.cmd_output.append(output)
            except Exception as e:
                sys.stdout = old_stdout
                self.cmd_output.append(f"错误: {e}")
        except Exception as e:
            sys.stdout = old_stdout
            self.cmd_output.append(f"错误: {e}")

        self.cmd_input.clear()

    def _create_database_viewer(self) -> QWidget:
        """创建数据库查看器"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 标题
        title = QLabel("数据库查看器")
        title.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # 表格选择
        table_layout = QHBoxLayout()
        table_layout.addWidget(QLabel("选择表:"))
        table_combo = QComboBox()
        table_combo.addItems(["用户表", "实验记录表", "模板表", "配置表"])
        table_layout.addWidget(table_combo)

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(lambda: logger.debug("刷新数据库表列表"))
        table_layout.addWidget(refresh_btn)
        table_layout.addStretch()
        layout.addLayout(table_layout)

        # 数据表格（使用文本框显示）
        from PySide6.QtWidgets import QHeaderView, QTableWidget

        table_widget = QTableWidget()
        table_widget.setColumnCount(5)
        table_widget.setHorizontalHeaderLabels(["ID", "名称", "类型", "值", "时间"])
        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_widget.setAlternatingRowColors(True)

        # 添加示例数据
        table_widget.setRowCount(3)
        from PySide6.QtWidgets import QTableWidgetItem

        table_widget.setItem(0, 0, QTableWidgetItem("1"))
        table_widget.setItem(0, 1, QTableWidgetItem("示例数据"))
        table_widget.setItem(0, 2, QTableWidgetItem("TEXT"))
        table_widget.setItem(0, 3, QTableWidgetItem("value"))
        table_widget.setItem(0, 4, QTableWidgetItem("2025-10-07"))

        layout.addWidget(table_widget)

        # 操作按钮
        button_layout = QHBoxLayout()
        query_btn = QPushButton("执行查询")
        query_btn.clicked.connect(lambda: logger.debug("执行SQL查询"))
        button_layout.addWidget(query_btn)

        export_btn = QPushButton("导出数据")
        export_btn.clicked.connect(lambda: logger.debug("导出数据库数据"))
        button_layout.addWidget(export_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # 提示信息
        info = QLabel("提示：此功能用于开发调试，请谨慎使用")
        info.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(info)

        return widget

    def _create_api_tester(self) -> QWidget:
        """创建API测试器"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 标题
        title = QLabel("API测试器")
        title.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # 请求方法和URL
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("方法:"))
        method_combo = QComboBox()
        method_combo.addItems(["GET", "POST", "PUT", "DELETE", "PATCH"])
        method_layout.addWidget(method_combo)

        method_layout.addWidget(QLabel("URL:"))
        url_input = QLineEdit()
        url_input.setPlaceholderText("输入API端点，例如: /api/experiments")
        method_layout.addWidget(url_input)
        layout.addLayout(method_layout)

        # 请求头
        headers_group = QGroupBox("请求头 (Headers)")
        headers_layout = QVBoxLayout(headers_group)
        headers_text = QTextEdit()
        headers_text.setPlaceholderText('{"Content-Type": "application/json"}')
        headers_text.setMaximumHeight(80)
        headers_layout.addWidget(headers_text)
        layout.addWidget(headers_group)

        # 请求体
        body_group = QGroupBox("请求体 (Body)")
        body_layout = QVBoxLayout(body_group)
        body_text = QTextEdit()
        body_text.setPlaceholderText('{"key": "value"}')
        body_text.setMaximumHeight(100)
        body_layout.addWidget(body_text)
        layout.addWidget(body_group)

        # 发送按钮
        send_btn = QPushButton("发送请求")
        send_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px; font-weight: bold;")

        def send_request():
            method = method_combo.currentText()
            url = url_input.text()
            logger.debug(f"发送 {method} 请求到: {url}")
            logger.info("API测试功能：模拟请求已发送")

        send_btn.clicked.connect(send_request)
        layout.addWidget(send_btn)

        # 响应区域
        response_group = QGroupBox("响应 (Response)")
        response_layout = QVBoxLayout(response_group)
        response_text = QTextEdit()
        response_text.setReadOnly(True)
        response_text.setPlaceholderText("响应结果将显示在这里...")
        response_layout.addWidget(response_text)
        layout.addWidget(response_group)

        # 提示信息
        info = QLabel("提示：此功能用于测试内部API接口")
        info.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(info)

        return widget

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.closed.emit()
        event.accept()
