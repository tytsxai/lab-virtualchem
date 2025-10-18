#!/usr/bin/env python3
"""
同步国际化键
从参考语言复制缺失的键到其他语言（保持原文或使用占位符）
"""

import json
import sys
from pathlib import Path
from typing import Any


def get_nested_value(data: dict, key_path: str) -> Any:
    """获取嵌套键的值"""
    keys = key_path.split(".")
    value = data
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return None
    return value


def set_nested_value(data: dict, key_path: str, value: Any) -> None:
    """设置嵌套键的值"""
    keys = key_path.split(".")
    current = data
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]
    current[keys[-1]] = value


def collect_all_keys(data: dict, prefix: str = "") -> set[str]:
    """收集所有键"""
    keys = set()
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        keys.add(full_key)
        if isinstance(value, dict):
            keys.update(collect_all_keys(value, full_key))
    return keys


def copy_structure(source: dict, target: dict, key_path: str = "") -> dict:
    """复制源结构到目标，保留目标已有的值"""
    result = {}

    for key, value in source.items():
        full_key = f"{key_path}.{key}" if key_path else key

        if isinstance(value, dict):
            # 递归处理字典
            target_value = target.get(key, {}) if isinstance(target.get(key), dict) else {}
            result[key] = copy_structure(value, target_value, full_key)
        else:
            # 如果目标已有值，保留；否则使用源值（需要翻译）
            if key in target:
                result[key] = target[key]
            else:
                # 使用源值作为占位符，标记为需要翻译
                result[key] = f"[TO_TRANSLATE] {value}"

    return result


def main():
    """主函数"""
    # 设置 Windows 控制台编码
    if sys.platform == "win32":
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("=" * 80)
    print("🔄 同步国际化键")
    print("=" * 80)
    print()

    i18n_dir = Path("assets/i18n")
    if not i18n_dir.exists():
        print(f"❌ 错误: 找不到 i18n 目录: {i18n_dir}")
        return 1

    # 读取参考语言
    reference_lang = "zh_CN"
    reference_file = i18n_dir / f"{reference_lang}.json"

    if not reference_file.exists():
        print(f"❌ 错误: 找不到参考语言文件: {reference_file}")
        return 1

    with open(reference_file, encoding="utf-8") as f:
        reference_data = json.load(f)

    reference_keys = collect_all_keys(reference_data)
    print(f"📊 参考语言 ({reference_lang}) 包含 {len(reference_keys)} 个键\n")

    # 处理每个语言文件
    updated_count = 0

    for lang_file in sorted(i18n_dir.glob("*.json")):
        if lang_file.name in ["languages.json", f"{reference_lang}.json"]:
            continue

        lang_code = lang_file.stem

        with open(lang_file, encoding="utf-8") as f:
            lang_data = json.load(f)

        lang_keys = collect_all_keys(lang_data)
        missing_keys = reference_keys - lang_keys

        if missing_keys:
            print(f"📝 {lang_code}: 添加 {len(missing_keys)} 个缺失的键...")

            # 复制结构
            updated_data = copy_structure(reference_data, lang_data)

            # 保存更新后的文件
            with open(lang_file, "w", encoding="utf-8") as f:
                json.dump(updated_data, f, ensure_ascii=False, indent=4)

            updated_count += 1
            print("   ✓ 已更新")
        else:
            print(f"✓ {lang_code}: 无需更新")

    print(f"\n✅ 同步完成! 更新了 {updated_count} 个语言文件")
    print("\n⚠️  注意: 新添加的键标记为 '[TO_TRANSLATE]'，需要进行实际翻译")

    return 0


if __name__ == "__main__":
    sys.exit(main())

