#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VirtualChemLab 热加载启动器
用于开发测试，代码更改后自动重启主程序
"""

import sys
import time
import subprocess
import argparse
from pathlib import Path
from typing import Optional

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
except ImportError:
    print("❌ 缺少依赖: watchdog")
    print("请安装: pip install watchdog")
    sys.exit(1)


class CodeChangeHandler(FileSystemEventHandler):
    """代码变更处理器"""
    
    def __init__(self, launcher):
        super().__init__()
        self.launcher = launcher
        self.last_reload_time = 0
        self.debounce_seconds = 2  # 防抖时间，避免短时间内多次重启
        
    def on_modified(self, event: FileSystemEvent):
        """文件修改事件"""
        if event.is_directory:
            return
        
        # 只监听Python文件和QML文件
        file_path = Path(event.src_path)
        if file_path.suffix not in ['.py', '.qml']:
            return
        
        # 忽略某些目录
        ignore_dirs = ['__pycache__', '.git', 'venv', 'dist', 'build', 'logs', 'data']
        if any(ignore_dir in file_path.parts for ignore_dir in ignore_dirs):
            return
        
        # 防抖：避免短时间内多次触发
        current_time = time.time()
        if current_time - self.last_reload_time < self.debounce_seconds:
            return
        
        self.last_reload_time = current_time
        
        print(f"\n🔄 检测到文件变更: {file_path.name}")
        print("⏳ 正在重启应用...")
        self.launcher.restart_app()


class HotReloadLauncher:
    """热加载启动器"""
    
    def __init__(self, command: str, watch_paths: list[str] = None):
        """
        初始化启动器
        
        Args:
            command: 启动命令
            watch_paths: 监听的目录列表
        """
        self.command = command
        self.process: Optional[subprocess.Popen] = None
        self.observer = Observer()
        self.project_root = Path(__file__).parent.parent.absolute()
        
        # 默认监听src目录
        if watch_paths is None:
            watch_paths = ['src']
        
        self.watch_paths = [self.project_root / path for path in watch_paths]
        
        print("=" * 60)
        print("🔥 VirtualChemLab 热加载启动器")
        print("=" * 60)
        print(f"📂 项目根目录: {self.project_root}")
        print(f"👁️  监听目录: {', '.join(str(p) for p in self.watch_paths)}")
        print(f"🚀 启动命令: {command}")
        print("=" * 60)
        print()
        
    def start_app(self):
        """启动应用"""
        try:
            print(f"▶️  启动应用...")
            self.process = subprocess.Popen(
                self.command,
                shell=True,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            print(f"✅ 应用已启动 (PID: {self.process.pid})")
            
            # 在后台线程中显示输出（可选）
            # 这里不显示，因为主程序会有自己的输出
            
        except Exception as e:
            print(f"❌ 启动失败: {e}")
            
    def stop_app(self):
        """停止应用"""
        if self.process and self.process.poll() is None:
            try:
                print("⏹️  停止应用...")
                self.process.terminate()
                
                # 等待最多5秒
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("⚠️  应用未响应，强制关闭...")
                    self.process.kill()
                    self.process.wait()
                
                print("✅ 应用已停止")
            except Exception as e:
                print(f"❌ 停止失败: {e}")
        
        self.process = None
        
    def restart_app(self):
        """重启应用"""
        self.stop_app()
        time.sleep(0.5)  # 短暂延迟确保完全停止
        self.start_app()
        
    def start_watching(self):
        """开始监听文件变更"""
        handler = CodeChangeHandler(self)
        
        for watch_path in self.watch_paths:
            if watch_path.exists():
                self.observer.schedule(handler, str(watch_path), recursive=True)
                print(f"👁️  开始监听: {watch_path}")
            else:
                print(f"⚠️  目录不存在: {watch_path}")
        
        self.observer.start()
        print()
        print("=" * 60)
        print("✅ 热加载已启动!")
        print("💡 修改代码后会自动重启应用")
        print("⚠️  按 Ctrl+C 停止")
        print("=" * 60)
        print()
        
    def run(self):
        """运行热加载"""
        try:
            # 首次启动应用
            self.start_app()
            
            # 开始监听文件变更
            self.start_watching()
            
            # 保持运行
            while True:
                time.sleep(1)
                
                # 检查进程是否意外退出
                if self.process and self.process.poll() is not None:
                    print("\n⚠️  应用意外退出")
                    print("🔄 3秒后自动重启...")
                    time.sleep(3)
                    self.start_app()
                    
        except KeyboardInterrupt:
            print("\n\n🛑 收到停止信号")
        finally:
            self.cleanup()
            
    def cleanup(self):
        """清理资源"""
        print("\n🧹 清理资源...")
        
        # 停止监听
        self.observer.stop()
        self.observer.join()
        
        # 停止应用
        self.stop_app()
        
        print("✅ 清理完成")
        print("👋 再见!")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="VirtualChemLab 热加载启动器 - 代码修改自动重启",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 热加载启动主程序
  python hot_reload_launcher.py
  
  # 指定启动命令
  python hot_reload_launcher.py --command "python main.py --skip-welcome"
  
  # 监听多个目录
  python hot_reload_launcher.py --watch src ui
  
  # 启动许可证模式
  python hot_reload_launcher.py --command "python src/main_with_license.py"
        """
    )
    
    parser.add_argument(
        '--command',
        type=str,
        default='python main.py',
        help='启动命令 (默认: python main.py)'
    )
    
    parser.add_argument(
        '--watch',
        type=str,
        nargs='+',
        default=['src'],
        help='监听的目录 (默认: src)'
    )
    
    args = parser.parse_args()
    
    # 创建启动器
    launcher = HotReloadLauncher(
        command=args.command,
        watch_paths=args.watch
    )
    
    # 运行
    launcher.run()


if __name__ == "__main__":
    main()

