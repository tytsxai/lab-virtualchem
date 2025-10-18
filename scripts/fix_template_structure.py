#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复interactive_experiment_template.yaml的结构
将顶级的steps、scoring等字段移到experiment节点下
"""

import sys
import yaml
from pathlib import Path

# Windows编码设置
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

def fix_template_structure():
    """修复模板结构"""
    template_file = Path("assets/templates/interactive_experiment_template.yaml")
    backup_file = Path("assets/templates/interactive_experiment_template.yaml.backup")

    print(f"📄 正在修复模板: {template_file}")

    # 1. 备份原文件
    if template_file.exists():
        import shutil
        shutil.copy2(template_file, backup_file)
        print(f"✅ 已备份到: {backup_file}")

    # 2. 读取YAML
    with open(template_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    print(f"\n🔍 原始结构:")
    print(f"   顶级键: {list(data.keys())}")
    print(f"   experiment键: {list(data['experiment'].keys())[:10]}")

    # 3. 移动字段
    fields_to_move = ['steps', 'scoring', 'achievements', 'experiment_flow', 'report']
    moved_fields = []

    for field in fields_to_move:
        if field in data:
            data['experiment'][field] = data.pop(field)
            moved_fields.append(field)
            print(f"   ✅ 移动 {field} 到 experiment 下")

    # 4. 写回文件
    with open(template_file, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False, indent=2)

    print(f"\n✅ 修复完成!")
    print(f"   移动了 {len(moved_fields)} 个字段: {', '.join(moved_fields)}")
    print(f"   新的experiment键数量: {len(data['experiment'])}")

    # 5. 验证
    with open(template_file, 'r', encoding='utf-8') as f:
        verify_data = yaml.safe_load(f)

    if 'steps' in verify_data['experiment']:
        print(f"\n✅ 验证成功: steps字段已在experiment节点下")
        print(f"   步骤数量: {len(verify_data['experiment']['steps'])}")
        return True
    else:
        print(f"\n❌ 验证失败: steps字段仍不在experiment节点下")
        return False

if __name__ == '__main__':
    try:
        success = fix_template_structure()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
