#!/usr/bin/env python3
"""
自动补全国际化翻译
从中文和英文版本复制缺失的键，使用英文作为临时翻译
"""

import json
import sys
from pathlib import Path


def deep_update(base: dict, updates: dict) -> dict:
    """深度更新字典"""
    result = base.copy()
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_update(result[key], value)
        else:
            result[key] = value
    return result


def main():
    """主函数"""
    # 设置 Windows 控制台编码
    if sys.platform == "win32":
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("=" * 80)
    print("🔄 自动补全国际化翻译")
    print("=" * 80)
    print()

    i18n_dir = Path("assets/i18n")

    # 读取参考文件
    print("📂 加载参考文件...")
    with open(i18n_dir / "zh_CN.json", encoding="utf-8") as f:
        zh_cn = json.load(f)

    with open(i18n_dir / "en_US.json", encoding="utf-8") as f:
        en_us = json.load(f)

    print("  ✓ zh_CN: 已加载")
    print("  ✓ en_US: 已加载\n")

    # 要更新的语言列表 (英文用完整的zh_CN结构,其他语言用en_US)
    languages_to_update = ["de_DE", "es_ES", "fr_FR", "ja_JP", "ko_KR"]

    print("📝 更新语言文件...")
    for lang_code in languages_to_update:
        lang_file = i18n_dir / f"{lang_code}.json"

        # 读取现有文件
        with open(lang_file, encoding="utf-8") as f:
            lang_data = json.load(f)

        # 使用英文作为基础(因为英文已经比较完整),然后合并现有翻译
        updated_data = deep_update(en_us, lang_data)

        # 保存
        with open(lang_file, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, ensure_ascii=False, indent=4)

        print(f"  ✓ {lang_code}: 已更新")

    # 确保en_US也有完整的结构
    print("\n📝 确保 en_US 完整...")
    en_updated = deep_update(zh_cn, en_us)
    with open(i18n_dir / "en_US.json", "w", encoding="utf-8") as f:
        json.dump(en_updated, f, ensure_ascii=False, indent=4)
    print("  ✓ en_US: 已更新")

    print("\n✅ 补全完成!")
    print("\n💡 说明:")
    print("   - 所有语言文件现在都有完整的键结构")
    print("   - 未翻译的内容暂时使用英文")
    print("   - 请运行验证工具检查: python tools/i18n_validator.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())

