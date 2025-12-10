#!/usr/bin/env python3
"""
虚拟化学实验室 开发者启动面板
统一的图形化启动管理界面
"""

import io
import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from src import __version__ as APP_VERSION

# 设置标准输出为UTF-8编码（Windows兼容）
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    except Exception:
        pass


class DeveloperPanel:
    """开发者启动面板主类"""

    def __init__(self, root):
        self.root = root
        self.root.title(f"虚拟化学实验室 开发者启动面板 v{APP_VERSION}")
        self.root.geometry("900x700")
        self.root.resizable(True, True)

        # 设置工作目录为项目根目录
        self.project_root = Path(__file__).parent.parent.absolute()
        os.chdir(self.project_root)

        # 当前运行的进程
        self.running_processes = {}

        # 创建界面
        self.create_ui()

        # 加载配置
        self.load_config()

    def create_ui(self):
        """创建用户界面"""
        # 设置样式
        style = ttk.Style()
        style.theme_use("clam")

        # 主容器
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(2, weight=1)

        # 标题
        title_frame = ttk.Frame(main_container)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        title_label = ttk.Label(title_frame, text="🧪 虚拟化学实验室 开发者启动面板", font=("Arial", 16, "bold"))
        title_label.pack()

        version_label = ttk.Label(title_frame, text=f"版本: v{APP_VERSION} | 开发者工具集", font=("Arial", 9))
        version_label.pack()

        # 创建标签页
        notebook = ttk.Notebook(main_container)
        notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # 主应用标签页
        app_frame = ttk.Frame(notebook, padding="10")
        notebook.add(app_frame, text="主应用")
        self.create_app_tab(app_frame)

        # 管理工具标签页
        admin_frame = ttk.Frame(notebook, padding="10")
        notebook.add(admin_frame, text="管理工具")
        self.create_admin_tab(admin_frame)

        # 许可证工具标签页
        license_frame = ttk.Frame(notebook, padding="10")
        notebook.add(license_frame, text="许可证")
        self.create_license_tab(license_frame)

        # 开发工具标签页
        dev_frame = ttk.Frame(notebook, padding="10")
        notebook.add(dev_frame, text="开发工具")
        self.create_dev_tab(dev_frame)

        # 系统工具标签页
        system_frame = ttk.Frame(notebook, padding="10")
        notebook.add(system_frame, text="系统工具")
        self.create_system_tab(system_frame)

        # 日志输出区域
        log_frame = ttk.LabelFrame(main_container, text="运行日志", padding="5")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 底部按钮栏
        button_frame = ttk.Frame(main_container)
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Button(button_frame, text="清空日志", command=self.clear_log).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="停止所有进程", command=self.stop_all_processes).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="刷新状态", command=self.refresh_status).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="退出", command=self.on_closing).pack(side=tk.RIGHT, padx=5)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_container, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

    def create_app_tab(self, parent):
        """创建主应用标签页"""
        # 标准启动
        frame1 = ttk.LabelFrame(parent, text="标准启动", padding="10")
        frame1.pack(fill=tk.X, pady=5)

        ttk.Label(frame1, text="学生实验模式 - 完整功能").pack(anchor=tk.W)
        ttk.Button(frame1, text="🚀 启动标准模式", command=lambda: self.run_command("python main.py", "标准模式")).pack(
            fill=tk.X, pady=5
        )

        # 快速启动
        frame2 = ttk.LabelFrame(parent, text="快速启动", padding="10")
        frame2.pack(fill=tk.X, pady=5)

        ttk.Label(frame2, text="跳过欢迎向导，快速进入实验").pack(anchor=tk.W)
        ttk.Button(
            frame2, text="⚡ 快速启动", command=lambda: self.run_command("python main.py --skip-welcome", "快速模式")
        ).pack(fill=tk.X, pady=5)

        # 热加载启动 (新增)
        frame_hot = ttk.LabelFrame(parent, text="🔥 热加载启动 (开发模式)", padding="10")
        frame_hot.pack(fill=tk.X, pady=5)

        ttk.Label(frame_hot, text="代码修改自动重启，便于开发测试").pack(anchor=tk.W)

        btn_frame = ttk.Frame(frame_hot)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            btn_frame, text="🔥 热加载模式", command=lambda: self.run_tool("hot_reload_launcher.py", "热加载模式")
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        ttk.Button(
            btn_frame,
            text="🔥 热加载+快速启动",
            command=lambda: self.run_tool(
                'hot_reload_launcher.py --command "python main.py --skip-welcome"', "热加载快速模式"
            ),
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        # 许可证验证启动
        frame3 = ttk.LabelFrame(parent, text="许可证验证启动", padding="10")
        frame3.pack(fill=tk.X, pady=5)

        ttk.Label(frame3, text="启动时验证许可证状态").pack(anchor=tk.W)
        ttk.Button(frame3, text="🔐 许可证模式启动", command=lambda: self.run_with_license_check()).pack(
            fill=tk.X, pady=5
        )

    def create_admin_tab(self, parent):
        """创建管理工具标签页"""
        # 教师控制台
        frame1 = ttk.LabelFrame(parent, text="教师控制台", padding="10")
        frame1.pack(fill=tk.X, pady=5)

        ttk.Label(frame1, text="管理学生实验、查看记录").pack(anchor=tk.W)
        ttk.Button(
            frame1, text="👨‍🏫 启动教师控制台", command=lambda: self.run_tool("teacher_console.py", "教师控制台")
        ).pack(fill=tk.X, pady=5)

        # 管理后台
        frame2 = ttk.LabelFrame(parent, text="管理后台", padding="10")
        frame2.pack(fill=tk.X, pady=5)

        ttk.Label(frame2, text="系统管理、用户管理、数据统计").pack(anchor=tk.W)
        ttk.Button(
            frame2,
            text="⚙️ 启动管理后台",
            command=lambda: self.run_tool("admin_server_start.py --host 127.0.0.1 --port 5000", "管理后台"),
        ).pack(fill=tk.X, pady=5)

        # 实验管理
        frame3 = ttk.LabelFrame(parent, text="实验管理工具", padding="10")
        frame3.pack(fill=tk.X, pady=5)

        ttk.Label(frame3, text="管理实验模板、实验数据").pack(anchor=tk.W)
        ttk.Button(
            frame3, text="🧪 启动实验管理", command=lambda: self.run_tool("experiment_manager_tool.py", "实验管理")
        ).pack(fill=tk.X, pady=5)

    def create_license_tab(self, parent):
        """创建许可证标签页"""
        # 基础操作
        frame1 = ttk.LabelFrame(parent, text="基础操作", padding="10")
        frame1.pack(fill=tk.X, pady=5)

        btn_frame = ttk.Frame(frame1)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            btn_frame,
            text="获取机器ID",
            command=lambda: self.run_tool("license_generator.py machine-id --non-interactive", "机器ID"),
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        ttk.Button(
            btn_frame,
            text="检查许可证",
            command=lambda: self.run_tool("license_generator.py check --non-interactive", "许可证检查"),
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        ttk.Button(
            btn_frame, text="健康检查", command=lambda: self.run_tool("license_health_check.py", "健康检查")
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        # 许可证工具箱
        frame2 = ttk.LabelFrame(parent, text="许可证工具箱", padding="10")
        frame2.pack(fill=tk.X, pady=5)

        ttk.Label(frame2, text="完整的许可证管理功能").pack(anchor=tk.W)

        btn_frame_license = ttk.Frame(frame2)
        btn_frame_license.pack(fill=tk.X, pady=5)

        ttk.Button(
            btn_frame_license,
            text="激活许可证",
            command=lambda: self.run_tool("license_generator.py activate", "激活许可证"),
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        ttk.Button(
            btn_frame_license,
            text="生成许可证",
            command=lambda: self.run_tool("license_generator.py generate", "生成许可证"),
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        # 备份恢复
        frame3 = ttk.LabelFrame(parent, text="备份与恢复", padding="10")
        frame3.pack(fill=tk.X, pady=5)

        btn_frame2 = ttk.Frame(frame3)
        btn_frame2.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame2, text="备份许可证", command=self.backup_license).pack(
            side=tk.LEFT, padx=2, fill=tk.X, expand=True
        )

        ttk.Button(
            btn_frame2,
            text="列出备份",
            command=lambda: self.run_tool("license_backup_tool.py list --dir data\\backups", "备份列表"),
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

    def create_dev_tab(self, parent):
        """创建开发工具标签页"""
        # 构建打包
        frame1 = ttk.LabelFrame(parent, text="构建与打包", padding="10")
        frame1.pack(fill=tk.X, pady=5)

        ttk.Label(frame1, text="使用PyInstaller构建可执行文件").pack(anchor=tk.W)
        ttk.Button(
            frame1, text="📦 构建应用", command=lambda: self.run_command("pyinstaller VirtualChemLab.spec", "构建")
        ).pack(fill=tk.X, pady=5)

        # 部署
        frame2 = ttk.LabelFrame(parent, text="部署工具", padding="10")
        frame2.pack(fill=tk.X, pady=5)

        ttk.Label(frame2, text="检查和安装依赖").pack(anchor=tk.W)

        btn_frame_deploy = ttk.Frame(frame2)
        btn_frame_deploy.pack(fill=tk.X, pady=5)

        ttk.Button(
            btn_frame_deploy,
            text="📦 安装依赖",
            command=lambda: self.run_command("pip install -r requirements.txt", "安装依赖"),
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        ttk.Button(
            btn_frame_deploy, text="🔍 检查环境", command=lambda: self.run_tool("system_health_check.py", "环境检查")
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        # 开发工具箱
        frame3 = ttk.LabelFrame(parent, text="开发工具箱", padding="10")
        frame3.pack(fill=tk.X, pady=5)

        ttk.Label(frame3, text="密钥生成、测试、代码检查等").pack(anchor=tk.W)

        btn_frame_tools = ttk.Frame(frame3)
        btn_frame_tools.pack(fill=tk.X, pady=5)

        ttk.Button(
            btn_frame_tools, text="🔑 生成密钥", command=lambda: self.run_tool("generate_secrets.py", "生成密钥")
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        ttk.Button(
            btn_frame_tools,
            text="✨ 代码格式化",
            command=lambda: self.run_command("black src/ tests/ tools/ --line-length 88", "代码格式化"),
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        # 测试工具
        frame4 = ttk.LabelFrame(parent, text="测试工具", padding="10")
        frame4.pack(fill=tk.X, pady=5)

        btn_frame = ttk.Frame(frame4)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="运行所有测试", command=lambda: self.run_command("pytest tests/ -v", "测试")).pack(
            side=tk.LEFT, padx=2, fill=tk.X, expand=True
        )

        ttk.Button(
            btn_frame, text="查看覆盖率", command=lambda: self.run_tool("test_coverage_tracker.py", "覆盖率")
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

    def create_system_tab(self, parent):
        """创建系统工具标签页"""
        # 系统维护
        frame1 = ttk.LabelFrame(parent, text="系统维护", padding="10")
        frame1.pack(fill=tk.X, pady=5)

        ttk.Label(frame1, text="缓存清理、问题诊断、系统修复").pack(anchor=tk.W)

        btn_frame_maint = ttk.Frame(frame1)
        btn_frame_maint.pack(fill=tk.X, pady=5)

        ttk.Button(
            btn_frame_maint, text="🔧 GUI维护工具", command=lambda: self.run_tool("maintenance_tool.py", "维护工具GUI")
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        ttk.Button(
            btn_frame_maint,
            text="🔧 修复问题",
            command=lambda: self.run_tool("maintenance_cli.py fix --all", "修复问题"),
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        # 用户流程检查
        frame2 = ttk.LabelFrame(parent, text="用户流程检查", padding="10")
        frame2.pack(fill=tk.X, pady=5)

        ttk.Label(frame2, text="检查用户操作流程完整性").pack(anchor=tk.W)
        ttk.Button(
            frame2, text="🔍 运行流程检查", command=lambda: self.run_tool("workflow_checker.py", "流程检查")
        ).pack(fill=tk.X, pady=5)

        # 快捷操作
        frame3 = ttk.LabelFrame(parent, text="快捷操作", padding="10")
        frame3.pack(fill=tk.X, pady=5)

        btn_frame = ttk.Frame(frame3)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            btn_frame, text="清理缓存", command=lambda: self.run_tool("maintenance_cli.py cleanup --all", "清理缓存")
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        ttk.Button(
            btn_frame, text="系统诊断", command=lambda: self.run_tool("maintenance_cli.py diagnose -v", "系统诊断")
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        ttk.Button(
            btn_frame, text="健康检查", command=lambda: self.run_tool("maintenance_cli.py health", "健康检查")
        ).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

    def run_command(self, command, name):
        """运行命令"""
        self.log(f"[{name}] 启动中...")
        self.status_var.set(f"▶️ 运行: {name}")

        def run_in_thread():
            try:
                # Windows下使用正确的编码
                if sys.platform == "win32":
                    process = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        cwd=self.project_root,
                        encoding="utf-8",
                        errors="replace",
                    )
                else:
                    process = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        cwd=self.project_root,
                    )

                self.running_processes[name] = process

                # 读取输出
                for line in process.stdout:
                    if line.strip():  # 只记录非空行
                        self.log(f"[{name}] {line.strip()}")

                process.wait()

                if name in self.running_processes:
                    del self.running_processes[name]

                if process.returncode == 0:
                    self.log(f"[{name}] ✅ 完成")
                else:
                    self.log(f"[{name}] ❌ 退出 (代码: {process.returncode})")

            except FileNotFoundError:
                self.log(f"[{name}] ❌ 错误: 命令未找到")
                messagebox.showerror("命令错误", f"无法执行命令: {command}\n请检查是否已安装相关工具")
            except Exception as e:
                self.log(f"[{name}] ❌ 错误: {str(e)}")
                messagebox.showerror("执行错误", f"执行失败: {str(e)}")
            finally:
                self.status_var.set("✅ 就绪")

        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()

    def run_tool(self, script, name):
        """运行tools目录下的工具"""
        script_parts = script.split()
        script_file = script_parts[0]
        script_path = self.project_root / "tools" / script_file

        if not script_path.exists():
            error_msg = f"找不到工具: {script_file}\n路径: {script_path}"
            messagebox.showerror("工具未找到", error_msg)
            self.log(f"[{name}] ❌ 错误: 文件不存在 - {script_file}")
            return

        # 构建完整命令
        command = f"python tools\\{script}"

        self.run_command(command, name)

    def run_bat_script(self, script, name):
        """运行批处理脚本"""
        script_path = self.project_root / script

        if not script_path.exists():
            messagebox.showerror("错误", f"找不到脚本: {script}")
            self.log(f"[{name}] 错误: 文件不存在")
            return

        # Windows下运行bat
        command = f'cmd /c "{script}"'
        self.run_command(command, name)

    def run_with_license_check(self):
        """带许可证验证的启动"""
        self.log("[许可证模式] 正在验证许可证...")

        # 先检查许可证
        check_cmd = "python tools\\license_generator.py check"

        def check_and_start():
            try:
                # 检查许可证
                result = subprocess.run(
                    check_cmd,
                    shell=True,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

                if result.returncode == 0:
                    self.log("[许可证] 验证通过")
                    self.log("[许可证] 正在启动应用...")
                    # 启动主程序
                    self.run_command("python main.py", "许可证模式")
                else:
                    self.log("[许可证] 验证失败")
                    self.log(result.stdout)
                    messagebox.showwarning("许可证验证", "许可证验证失败，是否继续以试用模式启动？")

            except Exception as e:
                self.log(f"[许可证] 错误: {str(e)}")

        thread = threading.Thread(target=check_and_start, daemon=True)
        thread.start()

    def backup_license(self):
        """备份许可证"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"data\\backups\\license_backup_{timestamp}.json"

        # 确保备份目录存在
        backup_dir = self.project_root / "data" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        self.run_tool(f"license_backup_tool.py backup {backup_file}", "许可证备份")

    def log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 添加状态图标
        if "错误" in message or "❌" in message or "失败" in message:
            icon = "❌"
        elif "警告" in message or "⚠" in message:
            icon = "⚠️"
        elif "成功" in message or "✅" in message or "完成" in message:
            icon = "✅"
        elif "启动" in message or "运行" in message:
            icon = "▶️"
        elif "停止" in message:
            icon = "⏹️"
        else:
            icon = "ℹ️"

        log_message = f"[{timestamp}] {icon} {message}\n"

        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.log("日志已清空")

    def stop_all_processes(self):
        """停止所有运行的进程"""
        if not self.running_processes:
            messagebox.showinfo("信息", "没有正在运行的进程")
            return

        if messagebox.askyesno("确认", f"确定要停止 {len(self.running_processes)} 个进程吗?"):
            for name, process in list(self.running_processes.items()):
                try:
                    process.terminate()
                    self.log(f"[{name}] 已停止")
                except Exception as e:
                    self.log(f"[{name}] 停止失败: {str(e)}")

            self.running_processes.clear()
            self.status_var.set("就绪")

    def refresh_status(self):
        """刷新状态"""
        self.log(f"当前运行进程: {len(self.running_processes)}")
        for name in self.running_processes.keys():
            self.log(f"  - {name}")

        if not self.running_processes:
            self.log("  无")

    def load_config(self):
        """加载配置"""
        config_path = self.project_root / "config.json"
        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    config = json.load(f)
                    self.log(f"已加载配置: {config_path}")
            except Exception as e:
                self.log(f"配置加载失败: {str(e)}")
        else:
            self.log("未找到配置文件")

        self.log("开发者面板已就绪")

    def on_closing(self):
        """关闭窗口时的处理"""
        if self.running_processes:
            if messagebox.askyesno("确认", "还有进程在运行，确定要退出吗？"):
                self.stop_all_processes()
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    """主函数"""
    root = tk.Tk()

    # 设置图标（如果存在）
    try:
        icon_path = Path(__file__).parent.parent / "assets" / "icon.ico"
        if icon_path.exists():
            root.iconbitmap(str(icon_path))
    except:
        pass

    app = DeveloperPanel(root)

    # 绑定关闭事件
    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    root.mainloop()


if __name__ == "__main__":
    main()
