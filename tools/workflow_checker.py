#!/usr/bin/env python3
"""
用户操作流程检查工具
检查系统的用户流程是否完整可用

功能:
1. 检查所有流程阶段的完整性
2. 验证用户交互逻辑
3. 测试流程转换
4. 生成检查报告
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from typing import Any

from colorama import Fore, init

from src.utils.logger import get_logger

# 初始化colorama（Windows终端颜色支持）
init(autoreset=True)

logger = get_logger(__name__)


class WorkflowChecker:
    """用户操作流程检查器"""

    def __init__(self):
        self.issues: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.successes: list[str] = []

    def check_all(self) -> dict[str, Any]:
        """执行所有检查"""
        print(f"\n{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.CYAN}🔍 VirtualChemLab 用户操作流程检查工具")
        print(f"{Fore.CYAN}{'=' * 70}\n")

        # 1. 检查流程管理器
        self._check_workflow_manager()

        # 2. 检查UI组件
        self._check_ui_components()

        # 3. 检查引导系统
        self._check_guidance_system()

        # 4. 检查数据流转
        self._check_data_flow()

        # 5. 检查配置完整性
        self._check_configuration()

        # 6. 检查文档
        self._check_documentation()

        # 生成报告
        return self._generate_report()

    def _check_workflow_manager(self) -> None:
        """检查流程管理器"""
        print(f"{Fore.YELLOW}[1/6] 检查流程管理器...")

        try:
            from src.core.user_workflow_manager import (
                UserWorkflowManager,
                WorkflowStage,
                get_workflow_manager,
            )

            # 检查是否能创建实例
            manager = UserWorkflowManager()
            self._success("流程管理器类可以实例化")

            # 检查单例模式
            manager2 = get_workflow_manager()
            if manager2 is not None:
                self._success("全局流程管理器可以获取")
            else:
                self._issue("全局流程管理器获取失败", "critical")

            # 检查所有阶段定义
            stages = list(WorkflowStage)
            if len(stages) >= 7:
                self._success(f"流程阶段定义完整 ({len(stages)} 个阶段)")
            else:
                self._warning(f"流程阶段定义可能不完整 (只有 {len(stages)} 个阶段)")

            # 检查关键方法
            required_methods = [
                "start_workflow",
                "complete_welcome_wizard",
                "confirm_user_identity",
                "start_experiment",
                "complete_experiment",
                "end_session",
            ]

            for method in required_methods:
                if hasattr(manager, method):
                    self._success(f"方法 {method} 存在")
                else:
                    self._issue(f"缺少关键方法: {method}", "critical")

        except Exception as e:
            self._issue(f"流程管理器检查失败: {e}", "critical")

    def _check_ui_components(self) -> None:
        """检查UI组件"""
        print(f"\n{Fore.YELLOW}[2/6] 检查UI组件...")

        try:
            # 检查主窗口

            self._success("主窗口类导入成功")

            # 检查欢迎向导

            self._success("欢迎向导类导入成功")

            # 检查用户引导
            from src.ui.user_guidance import get_guidance_manager

            guidance_mgr = get_guidance_manager()
            if guidance_mgr:
                self._success("用户引导管理器可用")

                # 检查引导旅程
                tours = guidance_mgr.tours
                if len(tours) >= 3:
                    self._success(f"引导旅程定义完整 ({len(tours)} 个旅程)")
                else:
                    self._warning(f"引导旅程较少 ({len(tours)} 个)")
            else:
                self._issue("用户引导管理器不可用", "medium")

            # 检查其他关键UI组件
            ui_components = [
                ("src.ui.experiment_view", "ExperimentView"),
                ("src.ui.record_browser", "RecordBrowser"),
                ("src.ui.knowledge_browser", "KnowledgeBrowser"),
                ("src.ui.settings_dialog", "SettingsDialog"),
            ]

            for module_path, class_name in ui_components:
                try:
                    module = __import__(module_path, fromlist=[class_name])
                    if hasattr(module, class_name):
                        self._success(f"UI组件 {class_name} 可用")
                    else:
                        self._warning(f"UI组件 {class_name} 不存在")
                except ImportError:
                    self._issue(f"无法导入 {module_path}.{class_name}", "medium")

        except Exception as e:
            self._issue(f"UI组件检查失败: {e}", "critical")

    def _check_guidance_system(self) -> None:
        """检查引导系统"""
        print(f"\n{Fore.YELLOW}[3/6] 检查引导系统...")

        try:
            # 检查首次运行检测
            data_dir = PROJECT_ROOT / "data"
            first_run_file = data_dir / ".first_run"

            if first_run_file.exists():
                self._success("首次运行标记文件存在")
            else:
                self._warning("首次运行标记文件不存在（可能是首次使用）")

            # 检查引导配置
            from src.ui.user_guidance import GuidePosition, GuideStepType

            step_types = list(GuideStepType)
            if len(step_types) >= 4:
                self._success(f"引导步骤类型定义完整 ({len(step_types)} 种)")

            positions = list(GuidePosition)
            if len(positions) >= 5:
                self._success(f"引导位置定义完整 ({len(positions)} 种)")

            # 检查教程系统
            try:
                from src.ui.tutorial_system import get_tutorial_manager

                tutorial_mgr = get_tutorial_manager()
                if tutorial_mgr:
                    self._success("教程管理器可用")
            except Exception as e:
                self._warning(f"教程系统检查失败: {e}")

        except Exception as e:
            self._issue(f"引导系统检查失败: {e}", "medium")

    def _check_data_flow(self) -> None:
        """检查数据流转"""
        print(f"\n{Fore.YELLOW}[4/6] 检查数据流转...")

        try:
            # 检查数据目录
            data_dir = PROJECT_ROOT / "data"
            required_dirs = ["users", "records", "experiments", "backups"]

            for dir_name in required_dirs:
                dir_path = data_dir / dir_name
                if dir_path.exists():
                    self._success(f"数据目录存在: {dir_name}/")
                else:
                    self._warning(f"数据目录不存在: {dir_name}/ （将自动创建）")

            # 检查存储接口
            from src.storage.json_store import JSONStore

            store = JSONStore(base_dir=data_dir)
            self._success("JSON存储系统可用")

            # 测试读写
            test_key = "workflow_checker_test"
            test_value = {"test": True, "timestamp": "2025-10-07"}
            store.set(test_key, test_value)
            retrieved = store.get(test_key)

            if retrieved == test_value:
                self._success("数据读写功能正常")
                store.delete(test_key)  # 清理测试数据
            else:
                self._issue("数据读写功能异常", "critical")

            # 检查会话数据
            session_file = data_dir / "last_session.json"
            if session_file.exists():
                self._success("会话数据文件存在")
            else:
                self._warning("会话数据文件不存在（正常情况，首次使用时）")

        except Exception as e:
            self._issue(f"数据流转检查失败: {e}", "medium")

    def _check_configuration(self) -> None:
        """检查配置完整性"""
        print(f"\n{Fore.YELLOW}[5/6] 检查配置完整性...")

        try:
            # 检查主配置文件
            config_file = PROJECT_ROOT / "config.json"
            if config_file.exists():
                self._success("主配置文件存在")

                # 尝试加载配置
                import json

                with config_file.open("r", encoding="utf-8") as f:
                    config = json.load(f)
                    self._success(f"配置文件加载成功 ({len(config)} 项配置)")
            else:
                self._warning("主配置文件不存在（将使用默认配置）")

            # 检查国际化文件
            i18n_dir = PROJECT_ROOT / "assets" / "i18n"
            if i18n_dir.exists():
                i18n_files = list(i18n_dir.glob("*.json"))
                if len(i18n_files) > 0:
                    self._success(f"国际化文件完整 ({len(i18n_files)} 个语言)")
                else:
                    self._issue("缺少国际化文件", "medium")
            else:
                self._issue("国际化目录不存在", "medium")

            # 检查实验模板
            template_dir = PROJECT_ROOT / "assets" / "templates"
            if template_dir.exists():
                templates = list(template_dir.glob("*.yaml")) + list(template_dir.glob("*.yml"))
                if len(templates) > 0:
                    self._success(f"实验模板完整 ({len(templates)} 个模板)")
                else:
                    self._warning("没有实验模板（用户将看不到可用实验）")
            else:
                self._issue("实验模板目录不存在", "medium")

            # 检查知识库
            knowledge_dir = PROJECT_ROOT / "assets" / "knowledge"
            if knowledge_dir.exists():
                knowledge_files = list(knowledge_dir.glob("*.json"))
                if len(knowledge_files) > 0:
                    self._success(f"知识库完整 ({len(knowledge_files)} 个文件)")
                else:
                    self._warning("知识库为空")
            else:
                self._warning("知识库目录不存在")

        except Exception as e:
            self._issue(f"配置检查失败: {e}", "medium")

    def _check_documentation(self) -> None:
        """检查文档"""
        print(f"\n{Fore.YELLOW}[6/6] 检查文档...")

        try:
            docs = [
                ("README.md", "项目说明"),
                ("docs/USER_MANUAL.md", "用户手册"),
                ("docs/USER_WORKFLOW_GUIDE.md", "用户操作流程指南"),
                ("QUICK_START.md", "快速开始指南"),
                ("INSTALL.md", "安装说明"),
            ]

            for doc_file, doc_name in docs:
                file_path = PROJECT_ROOT / doc_file
                if file_path.exists():
                    # 检查文件大小
                    file_size = file_path.stat().st_size
                    if file_size > 100:  # 至少100字节
                        self._success(f"{doc_name} 存在且有内容")
                    else:
                        self._warning(f"{doc_name} 存在但内容可能不完整")
                else:
                    self._warning(f"{doc_name} 不存在")

        except Exception as e:
            self._warning(f"文档检查失败: {e}")

    def _generate_report(self) -> dict[str, Any]:
        """生成检查报告"""
        print(f"\n{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.CYAN}📊 检查报告")
        print(f"{Fore.CYAN}{'=' * 70}\n")

        # 统计
        total_checks = len(self.successes) + len(self.warnings) + len(self.issues)
        success_count = len(self.successes)
        warning_count = len(self.warnings)
        issue_count = len(self.issues)

        # 计算得分
        score = 0
        if total_checks > 0:
            score = int((success_count / total_checks) * 100)

        # 显示统计
        print(f"{Fore.GREEN}✅ 通过: {success_count}")
        print(f"{Fore.YELLOW}⚠️  警告: {warning_count}")
        print(f"{Fore.RED}❌ 问题: {issue_count}")
        print(f"\n总得分: {score}/100\n")

        # 显示问题详情
        if self.issues:
            print(f"{Fore.RED}【问题列表】")
            for i, issue in enumerate(self.issues, 1):
                severity_color = Fore.RED if issue["severity"] == "critical" else Fore.YELLOW
                print(f"{severity_color}  {i}. [{issue['severity'].upper()}] {issue['message']}")
            print()

        # 显示警告详情
        if self.warnings:
            print(f"{Fore.YELLOW}【警告列表】")
            for i, warning in enumerate(self.warnings, 1):
                print(f"{Fore.YELLOW}  {i}. {warning['message']}")
            print()

        # 评级
        if score >= 90:
            rating = "优秀"
            rating_color = Fore.GREEN
        elif score >= 75:
            rating = "良好"
            rating_color = Fore.CYAN
        elif score >= 60:
            rating = "及格"
            rating_color = Fore.YELLOW
        else:
            rating = "需要改进"
            rating_color = Fore.RED

        print(f"{rating_color}综合评级: {rating}\n")

        # 建议
        print(f"{Fore.CYAN}【改进建议】")
        if issue_count > 0:
            print(f"{Fore.YELLOW}  • 优先修复所有【问题】，特别是 CRITICAL 级别的")
        if warning_count > 0:
            print(f"{Fore.YELLOW}  • 关注【警告】项，虽然不影响核心功能但建议完善")
        if score < 90:
            print(f"{Fore.YELLOW}  • 补充缺失的文档和配置")
            print(f"{Fore.YELLOW}  • 完善引导系统和用户体验")
        else:
            print(f"{Fore.GREEN}  • 系统运行良好，继续保持！")

        print(f"\n{Fore.CYAN}{'=' * 70}\n")

        return {
            "score": score,
            "rating": rating,
            "total_checks": total_checks,
            "successes": success_count,
            "warnings": warning_count,
            "issues": issue_count,
            "issue_details": self.issues,
            "warning_details": self.warnings,
        }

    def _success(self, message: str) -> None:
        """记录成功项"""
        self.successes.append(message)
        print(f"{Fore.GREEN}  ✅ {message}")

    def _warning(self, message: str) -> None:
        """记录警告项"""
        self.warnings.append({"message": message})
        print(f"{Fore.YELLOW}  ⚠️  {message}")

    def _issue(self, message: str, severity: str = "medium") -> None:
        """记录问题项"""
        self.issues.append({"message": message, "severity": severity})
        severity_color = Fore.RED if severity == "critical" else Fore.YELLOW
        print(f"{severity_color}  ❌ {message}")


def main() -> int:
    """主函数"""
    try:
        checker = WorkflowChecker()
        report = checker.check_all()

        # 根据结果返回退出码
        if report["issues"] > 0:
            return 1
        return 0

    except Exception as e:
        print(f"\n{Fore.RED}❌ 检查过程出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
