#!/usr/bin/env python
"""
插件管理命令行工具
"""

import argparse
import logging
import subprocess
import sys

from . import registry

logger = logging.getLogger(__name__)

# 推荐的插件组合
RECOMMENDED_PLUGINS = ["rdkit", "reportlab"]

# 所有可选插件
ALL_PLUGINS = ["rdkit", "pyqtgraph", "reportlab", "weasyprint", "cantera", "openmm"]

# 插件到包名的映射
PLUGIN_TO_PACKAGE = {
    "rdkit": "rdkit",
    "pyqtgraph": "pyqtgraph",
    "reportlab": "reportlab",
    "weasyprint": "weasyprint",
    "cantera": "cantera",
    "openmm": None,  # OpenMM 推荐用 conda 安装
}


def show_status():
    """显示所有插件状态"""
    print("\n" + "=" * 60)
    logger.info("VirtualChemLab 插件状态")
    print("=" * 60 + "\n")

    plugins = registry.list_plugins()

    if not plugins:
        logger.info("未找到任何插件")
        return

    for name, info in plugins.items():
        status_icon = {
            "available": "[+]",
            "not_installed": "[-]",
            "error": "[!]",
            "disabled": "[X]",
        }.get(info.status.value, "[?]")

        logger.info(f"{status_icon} {name}")
        logger.info(f"   描述: {info.description}")
        logger.info(f"   许可证: {info.license}")
        logger.info(f"   状态: {info.status.value}")

        if info.version:
            logger.info(f"   版本: {info.version}")

        if info.error_msg:
            logger.info(f"   错误: {info.error_msg}")

        print()

    # 统计
    total = len(plugins)
    available = sum(1 for p in plugins.values() if p.status.value == "available")
    logger.info(f"总计: {available}/{total} 个插件可用\n")


def install_plugins(plugin_names: list[str], use_conda: bool = False):
    """安装插件

    Args:
        plugin_names: 插件名称列表
        use_conda: 是否使用 conda
    """
    logger.info("\n开始安装插件...\n")

    for plugin_name in plugin_names:
        package_name = PLUGIN_TO_PACKAGE.get(plugin_name)

        if package_name is None:
            if plugin_name == "openmm":
                logger.info(f"⚠️  {plugin_name}: 推荐使用 conda 安装")
                logger.info("    命令: conda install -c conda-forge openmm\n")
            else:
                logger.info(f"❌ {plugin_name}: 未知插件\n")
            continue

        # 检查是否已安装
        if registry.is_available(plugin_name):
            info = registry.get_info(plugin_name)
            logger.info(f"✅ {plugin_name} 已安装 (版本: {info.version})\n")
            continue

        # 安装
        logger.info(f"📦 正在安装 {plugin_name}...")

        try:
            if use_conda:
                cmd = ["conda", "install", "-y", package_name]
            else:
                cmd = [sys.executable, "-m", "pip", "install", package_name]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"✅ {plugin_name} 安装成功\n")
                # 重新尝试加载
                registry._try_load(plugin_name)
            else:
                logger.info(f"❌ {plugin_name} 安装失败")
                logger.info(f"   错误: {result.stderr}\n")

        except Exception as e:
            logger.info(f"❌ {plugin_name} 安装失败: {e}\n")


def install_recommended():
    """安装推荐插件"""
    print("\n安装推荐插件: " + ", ".join(RECOMMENDED_PLUGINS))
    install_plugins(RECOMMENDED_PLUGINS)


def install_all():
    """安装所有插件"""
    logger.info("\n安装所有插件...")

    # 排除 OpenMM（需要特殊处理）
    pip_plugins = [p for p in ALL_PLUGINS if p != "openmm"]
    install_plugins(pip_plugins)

    logger.info("\n注意: OpenMM 推荐使用以下命令安装:")
    logger.info("  conda install -c conda-forge openmm\n")


def show_info(plugin_name: str):
    """显示插件详细信息"""
    info = registry.get_info(plugin_name)

    if not info:
        logger.info(f"\n❌ 未找到插件: {plugin_name}\n")
        return

    logger.info(f"\n插件信息: {plugin_name}")
    print("=" * 40)
    logger.info(f"描述: {info.description}")
    logger.info(f"模块: {info.module_name}")
    logger.info(f"许可证: {info.license}")
    logger.info(f"状态: {info.status.value}")

    if info.version:
        logger.info(f"版本: {info.version}")

    if info.error_msg:
        logger.error(f"{info.error_msg}")

    # 安装建议
    if info.status.value == "not_installed":
        package_name = PLUGIN_TO_PACKAGE.get(plugin_name)
        if package_name:
            logger.info(f"\n安装命令: pip install {package_name}")
        elif plugin_name == "openmm":
            logger.info("\n安装命令: conda install -c conda-forge openmm")

    print()


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="VirtualChemLab 插件管理工具")

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # status 命令
    subparsers.add_parser("status", help="显示所有插件状态")

    # install 命令
    install_parser = subparsers.add_parser("install", help="安装插件")
    install_parser.add_argument("plugins", nargs="*", help="要安装的插件名称")
    install_parser.add_argument(
        "--recommended", action="store_true", help="安装推荐插件"
    )
    install_parser.add_argument("--all", action="store_true", help="安装所有插件")
    install_parser.add_argument("--conda", action="store_true", help="使用 conda 安装")

    # info 命令
    info_parser = subparsers.add_parser("info", help="显示插件详细信息")
    info_parser.add_argument("plugin", help="插件名称")

    # list 命令
    subparsers.add_parser("list", help="列出所有可用插件名称")

    args = parser.parse_args()

    if args.command == "status":
        show_status()

    elif args.command == "install":
        if args.recommended:
            install_recommended()
        elif args.all:
            install_all()
        elif args.plugins:
            install_plugins(args.plugins, use_conda=args.conda)
        else:
            logger.info("\n请指定要安装的插件，或使用 --recommended / --all\n")

    elif args.command == "info":
        show_info(args.plugin)

    elif args.command == "list":
        plugins = registry.list_plugins()
        logger.info("\n可用插件:")
        for name in plugins:
            logger.info(f"  - {name}")
        print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
