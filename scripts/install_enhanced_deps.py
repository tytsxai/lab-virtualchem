#!/usr/bin/env python
"""
智能安装增强依赖脚本
根据用户需求选择性安装增强功能
"""

import subprocess


def run_command(cmd: str):
    """执行命令"""
    print(f"执行: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ 错误: {result.stderr}")
        return False
    print("✅ 成功")
    return True


def main():
    """主函数"""
    print("="*60)
    print("VirtualChemLab 增强功能安装向导")
    print("="*60 + "\n")

    print("请选择要安装的功能模块:\n")

    options = {
        '1': {
            'name': 'AI增强功能 (LangChain + OpenAI)',
            'packages': ['langchain>=0.1.0', 'langchain-openai>=0.0.5', 'langchain-community>=0.0.20', 'openai>=1.0.0', 'chromadb>=0.4.0']
        },
        '2': {
            'name': '文档生成 (Sphinx)',
            'packages': ['sphinx>=7.0.0', 'sphinx-rtd-theme>=2.0.0', 'sphinx-autodoc-typehints>=1.25.0']
        },
        '3': {
            'name': '化学数据库 (PubChemPy)',
            'packages': ['pubchempy>=1.0.0']
        },
        '4': {
            'name': 'UI增强 (图标+单位转换)',
            'packages': ['qtawesome>=1.3.0', 'pint>=0.23']
        },
        '5': {
            'name': '数据存储增强 (TinyDB)',
            'packages': ['tinydb>=4.8.0']
        },
        '6': {
            'name': '测试与质量保证 (Hypothesis + Bandit)',
            'packages': ['hypothesis>=6.100.0', 'bandit>=1.7.0']
        },
        '7': {
            'name': 'Web控制台 (Streamlit)',
            'packages': ['streamlit>=1.30.0']
        },
        '8': {
            'name': '全部安装 (所有增强功能)',
            'packages': ['requirements-enhanced.txt']
        }
    }

    for key, option in options.items():
        print(f"{key}. {option['name']}")

    print("\n0. 退出")
    print()

    # 获取用户选择
    choices = input("请输入选项 (多选用逗号分隔，如: 1,2,3): ").strip()

    if choices == '0':
        print("已取消安装")
        return

    # 处理选择
    selected = [c.strip() for c in choices.split(',') if c.strip() in options]

    if not selected:
        print("无效的选择")
        return

    # 安装包
    print(f"\n开始安装 {len(selected)} 个模块...\n")

    for choice in selected:
        option = options[choice]
        print(f"\n📦 安装: {option['name']}")
        print("-" * 60)

        packages = option['packages']

        if choice == '8':  # 全部安装
            cmd = f"pip install -r {packages[0]}"
        else:
            cmd = f"pip install {' '.join(packages)}"

        if not run_command(cmd):
            print(f"⚠️  {option['name']} 安装失败，继续安装其他模块...")

    print("\n" + "="*60)
    print("安装完成!")
    print("="*60)
    print("\n运行健康检查以验证安装:")
    print("  python scripts/check_integration_health.py")
    print()


if __name__ == '__main__':
    main()

