#!/usr/bin/env python3
"""
国际化验证工具
检查所有语言文件的翻译完整性和一致性
"""

import json
import sys
from pathlib import Path
from typing import Any


class I18nValidator:
    """国际化验证器"""

    def __init__(self, i18n_dir: Path):
        self.i18n_dir = i18n_dir
        self.languages: dict[str, dict] = {}
        self.reference_lang = "zh_CN"  # 使用中文作为参考语言
        self.all_keys: set[str] = set()
        self.issues: list[dict[str, Any]] = []

    def load_languages(self) -> None:
        """加载所有语言文件"""
        print("📂 加载语言文件...")
        for lang_file in self.i18n_dir.glob("*.json"):
            if lang_file.name == "languages.json":
                continue

            lang_code = lang_file.stem
            try:
                with open(lang_file, encoding="utf-8") as f:
                    self.languages[lang_code] = json.load(f)
                    print(f"  ✓ {lang_code}: {lang_file.name}")
            except Exception as e:
                print(f"  ✗ {lang_code}: 加载失败 - {e}")
                self.issues.append(
                    {
                        "type": "load_error",
                        "language": lang_code,
                        "file": str(lang_file),
                        "error": str(e),
                    }
                )

    def collect_all_keys(self, data: dict, prefix: str = "") -> set[str]:
        """递归收集所有键"""
        keys = set()
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.add(full_key)
            if isinstance(value, dict):
                keys.update(self.collect_all_keys(value, full_key))
        return keys

    def validate_completeness(self) -> None:
        """验证翻译完整性"""
        print("\n🔍 检查翻译完整性...")

        if self.reference_lang not in self.languages:
            print(f"  ✗ 参考语言 {self.reference_lang} 不存在!")
            return

        # 收集参考语言的所有键
        reference_data = self.languages[self.reference_lang]
        reference_keys = self.collect_all_keys(reference_data)
        self.all_keys = reference_keys

        print(f"  📊 参考语言 ({self.reference_lang}) 包含 {len(reference_keys)} 个键\n")

        # 检查每个语言
        for lang_code, lang_data in self.languages.items():
            if lang_code == self.reference_lang:
                continue

            lang_keys = self.collect_all_keys(lang_data)

            # 检查缺失的键
            missing_keys = reference_keys - lang_keys
            # 检查多余的键
            extra_keys = lang_keys - reference_keys

            completion = (len(lang_keys) - len(extra_keys)) / len(reference_keys) * 100 if reference_keys else 0

            print(f"  📋 {lang_code}:")
            print(f"     完成度: {completion:.1f}% ({len(lang_keys)}/{len(reference_keys)} 键)")

            if missing_keys:
                print(f"     ⚠️  缺失 {len(missing_keys)} 个键:")
                for key in sorted(missing_keys)[:5]:  # 只显示前5个
                    print(f"        - {key}")
                if len(missing_keys) > 5:
                    print(f"        ... 和其他 {len(missing_keys) - 5} 个键")

                self.issues.append(
                    {
                        "type": "missing_keys",
                        "language": lang_code,
                        "count": len(missing_keys),
                        "keys": list(missing_keys),
                    }
                )

            if extra_keys:
                print(f"     ⚠️  多余 {len(extra_keys)} 个键:")
                for key in sorted(extra_keys)[:3]:
                    print(f"        - {key}")
                if len(extra_keys) > 3:
                    print(f"        ... 和其他 {len(extra_keys) - 3} 个键")

                self.issues.append(
                    {
                        "type": "extra_keys",
                        "language": lang_code,
                        "count": len(extra_keys),
                        "keys": list(extra_keys),
                    }
                )

            if not missing_keys and not extra_keys:
                print("     ✅ 完整")

            print()

    def validate_structure(self) -> None:
        """验证结构一致性"""
        print("🏗️  检查结构一致性...")

        reference_data = self.languages.get(self.reference_lang, {})

        for lang_code, lang_data in self.languages.items():
            if lang_code == self.reference_lang:
                continue

            issues_found = self._compare_structure(reference_data, lang_data, lang_code, "")

            if not issues_found:
                print(f"  ✓ {lang_code}: 结构一致")

    def _compare_structure(self, ref_data: dict, lang_data: dict, lang_code: str, prefix: str) -> bool:
        """比较两个数据结构"""
        issues_found = False

        for key, ref_value in ref_data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if key not in lang_data:
                continue  # 缺失的键已在完整性检查中报告

            lang_value = lang_data[key]

            # 检查类型是否一致
            if type(ref_value) != type(lang_value):
                print(
                    f"  ✗ {lang_code}: {full_key} - 类型不匹配 (参考: {type(ref_value).__name__}, 实际: {type(lang_value).__name__})"
                )
                self.issues.append(
                    {
                        "type": "type_mismatch",
                        "language": lang_code,
                        "key": full_key,
                        "expected_type": type(ref_value).__name__,
                        "actual_type": type(lang_value).__name__,
                    }
                )
                issues_found = True
                continue

            # 递归检查嵌套字典
            if isinstance(ref_value, dict):
                nested_issues = self._compare_structure(ref_value, lang_value, lang_code, full_key)
                issues_found = issues_found or nested_issues

        return issues_found

    def check_button_texts(self) -> None:
        """检查按钮文本的翻译"""
        print("\n🔘 检查按钮文本...")

        button_keys = [
            "ui.confirm",
            "ui.cancel",
            "ui.close",
            "ui.retry",
            "ui.submit",
            "ui.next",
            "ui.previous",
            "step.next",
            "step.previous",
            "step.confirm",
            "step.submit",
            "settings.save",
            "settings.reset_defaults",
            "wizard.skip",
            "wizard.previous",
            "wizard.next",
            "wizard.finish",
        ]

        for lang_code, lang_data in self.languages.items():
            missing_buttons = []
            for key in button_keys:
                if not self._get_nested_value(lang_data, key):
                    missing_buttons.append(key)

            if missing_buttons:
                print(f"  ⚠️  {lang_code} 缺失按钮文本:")
                for key in missing_buttons:
                    print(f"     - {key}")
                self.issues.append(
                    {
                        "type": "missing_button_text",
                        "language": lang_code,
                        "keys": missing_buttons,
                    }
                )
            else:
                print(f"  ✓ {lang_code}: 所有按钮文本完整")

    def check_message_prompts(self) -> None:
        """检查消息提示的翻译"""
        print("\n💬 检查消息提示...")

        message_keys = [
            "message.confirm_exit",
            "message.confirm_restart",
            "message.experiment_completed",
            "message.loading",
            "message.saving",
            "message.error",
            "message.success",
            "ui.info",
            "ui.warning",
            "ui.error",
            "ui.success",
        ]

        for lang_code, lang_data in self.languages.items():
            missing_messages = []
            for key in message_keys:
                if not self._get_nested_value(lang_data, key):
                    missing_messages.append(key)

            if missing_messages:
                print(f"  ⚠️  {lang_code} 缺失消息提示:")
                for key in missing_messages:
                    print(f"     - {key}")
                self.issues.append(
                    {
                        "type": "missing_message_prompt",
                        "language": lang_code,
                        "keys": missing_messages,
                    }
                )
            else:
                print(f"  ✓ {lang_code}: 所有消息提示完整")

    def _get_nested_value(self, data: dict, key: str) -> Any:
        """获取嵌套值"""
        keys = key.split(".")
        value = data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        return value

    def generate_report(self) -> None:
        """生成验证报告"""
        print("\n" + "=" * 80)
        print("📊 验证报告摘要")
        print("=" * 80)

        # 统计
        total_languages = len(self.languages)
        total_issues = len(self.issues)

        print(f"\n语言总数: {total_languages}")
        print(f"参考语言: {self.reference_lang}")
        print(f"总键数: {len(self.all_keys)}")
        print(f"发现问题: {total_issues}\n")

        # 按类型分组问题
        issues_by_type: dict[str, list] = {}
        for issue in self.issues:
            issue_type = issue["type"]
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)

        # 显示问题摘要
        if issues_by_type:
            print("问题分类:")
            for issue_type, issues in issues_by_type.items():
                print(f"  • {issue_type}: {len(issues)} 个")
        else:
            print("✅ 未发现任何问题!")

        # 语言完成度表
        print("\n语言完成度:")
        print("-" * 60)
        print(f"{'语言':<15} {'完成度':<15} {'状态':<30}")
        print("-" * 60)

        reference_keys_count = len(self.all_keys)
        for lang_code in sorted(self.languages.keys()):
            lang_data = self.languages[lang_code]
            lang_keys = self.collect_all_keys(lang_data)
            completion = len(lang_keys) / reference_keys_count * 100 if reference_keys_count else 0

            status = "✅ 完整" if completion >= 100 else f"⚠️  {100 - completion:.1f}% 待完成"
            print(f"{lang_code:<15} {completion:>6.1f}%        {status}")

        print("-" * 60)

        # 保存详细报告
        report_file = Path("reports/i18n_validation_report.json")
        report_file.parent.mkdir(parents=True, exist_ok=True)

        report_data = {
            "timestamp": Path(__file__).stat().st_mtime,
            "summary": {
                "total_languages": total_languages,
                "reference_language": self.reference_lang,
                "total_keys": len(self.all_keys),
                "total_issues": total_issues,
            },
            "languages": {},
            "issues": self.issues,
        }

        for lang_code, lang_data in self.languages.items():
            lang_keys = self.collect_all_keys(lang_data)
            completion = len(lang_keys) / reference_keys_count * 100 if reference_keys_count else 0

            report_data["languages"][lang_code] = {
                "total_keys": len(lang_keys),
                "completion": round(completion, 2),
                "missing_keys": len(self.all_keys - lang_keys),
            }

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        print(f"\n📄 详细报告已保存到: {report_file}")

        # 返回状态码
        return 0 if total_issues == 0 else 1


def main():
    """主函数"""
    # 设置 Windows 控制台编码
    if sys.platform == "win32":
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("=" * 80)
    print("🌍 VirtualChemLab 国际化验证工具")
    print("=" * 80)
    print()

    i18n_dir = Path("assets/i18n")
    if not i18n_dir.exists():
        print(f"❌ 错误: 找不到 i18n 目录: {i18n_dir}")
        return 1

    validator = I18nValidator(i18n_dir)

    # 执行验证
    validator.load_languages()
    validator.validate_completeness()
    validator.validate_structure()
    validator.check_button_texts()
    validator.check_message_prompts()

    # 生成报告
    exit_code = validator.generate_report()

    print("\n验证完成!")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
