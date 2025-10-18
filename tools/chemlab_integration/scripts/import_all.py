#!/usr/bin/env python3
"""一键导入所有 chemlab 数据

将 chemlab 的实验案例和知识库数据导入到 VirtualChemLab。
"""

import argparse
import logging
import sys
from pathlib import Path

import colorlog
import yaml

# 添加项目路径
TOOL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(TOOL_ROOT))

from src.converters.card_converter import CardConverter  # noqa: E402
from src.converters.template_converter import TemplateConverter  # noqa: E402
from src.fetcher import ChemLabFetcher  # noqa: E402
from src.parsers.experiment_parser import ExperimentParser  # noqa: E402
from src.parsers.knowledge_parser import KnowledgeParser  # noqa: E402
from src.validators.schema_validator import validate_directory  # noqa: E402

# 配置彩色日志
handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s",
        log_colors={"DEBUG": "cyan", "INFO": "green", "WARNING": "yellow", "ERROR": "red", "CRITICAL": "red,bg_white"},
    )
)

logger = colorlog.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def load_config(config_path: Path) -> dict:
    """加载配置文件"""
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def backup_existing_data(config: dict):
    """备份现有数据"""
    backup_config = config.get("output", {}).get("backup", {})

    if not backup_config.get("enabled", True):
        logger.info("备份功能已禁用,跳过备份")
        return

    import shutil
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(backup_config.get("backup_dir", "./backups")) / timestamp

    # 备份实验模板
    exp_dir = Path(config["output"]["experiments_dir"])
    if exp_dir.exists():
        backup_exp_dir = backup_dir / "templates"
        backup_exp_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(exp_dir, backup_exp_dir, dirs_exist_ok=True)
        logger.info(f"✅ 备份实验模板到: {backup_exp_dir}")

    # 备份知识库
    knowledge_dir = Path(config["output"]["knowledge_dir"])
    if knowledge_dir.exists():
        backup_knowledge_dir = backup_dir / "knowledge"
        backup_knowledge_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(knowledge_dir, backup_knowledge_dir, dirs_exist_ok=True)
        logger.info(f"✅ 备份知识库到: {backup_knowledge_dir}")


def import_experiments(fetcher: ChemLabFetcher, config: dict) -> int:
    """导入实验数据

    Returns:
        成功导入的数量
    """
    logger.info("\n" + "=" * 60)
    logger.info("开始导入实验数据...")
    logger.info("=" * 60)

    # 1. 获取示例文件
    example_files = fetcher.list_examples()
    logger.info(f"找到 {len(example_files)} 个示例文件")

    if not example_files:
        logger.warning("未找到示例文件,跳过实验导入")
        return 0

    # 应用过滤器
    filters = config.get("filters", {}).get("experiments", {})
    min_steps = filters.get("min_steps", 0)
    max_steps = filters.get("max_steps", 999)

    # 2. 解析实验
    parser = ExperimentParser()
    experiments = parser.parse_batch(example_files)

    # 过滤
    filtered_experiments = [exp for exp in experiments if min_steps <= len(exp.get("steps", [])) <= max_steps]

    logger.info(f"解析后筛选: {len(filtered_experiments)}/{len(experiments)} 个实验符合条件")

    # 3. 转换为模板
    converter = TemplateConverter(config)
    output_dir = Path(config["output"]["experiments_dir"])
    repo_info = fetcher.get_repo_info()

    saved_files = converter.convert_batch(filtered_experiments, output_dir, repo_info)

    logger.info(f"✅ 成功导入 {len(saved_files)} 个实验模板到: {output_dir}")

    return len(saved_files)


def import_knowledge(fetcher: ChemLabFetcher, config: dict) -> int:
    """导入知识库数据

    Returns:
        成功导入的数量
    """
    logger.info("\n" + "=" * 60)
    logger.info("开始导入知识库数据...")
    logger.info("=" * 60)

    # 1. 获取数据文件
    data_files = fetcher.list_molecule_data()
    logger.info(f"找到 {len(data_files)} 个数据文件")

    if not data_files:
        logger.warning("未找到数据文件,跳过知识库导入")
        return 0

    # 2. 解析知识
    parser = KnowledgeParser()
    knowledge_data = parser.parse_batch(data_files)

    # 应用过滤器
    filters = config.get("filters", {}).get("knowledge", {})
    include_types = filters.get("include_types", ["reagent", "apparatus", "procedure"])

    # 过滤类型
    filtered_knowledge = {k: v for k, v in knowledge_data.items() if k in include_types}

    # 3. 转换为知识卡片
    converter = CardConverter(config)
    output_dir = Path(config["output"]["knowledge_dir"])
    repo_info = fetcher.get_repo_info()

    saved_files = converter.convert_batch(filtered_knowledge, output_dir, repo_info)

    total_count = sum(len(files) for files in saved_files.values())
    logger.info(f"✅ 成功导入 {total_count} 个知识卡片到: {output_dir}")

    return total_count


def validate_imported_data(config: dict):
    """验证导入的数据"""
    logger.info("\n" + "=" * 60)
    logger.info("开始验证导入的数据...")
    logger.info("=" * 60)

    # 验证实验模板
    exp_dir = Path(config["output"]["experiments_dir"])
    if exp_dir.exists():
        logger.info(f"\n验证实验模板: {exp_dir}")
        success, fail, errors = validate_directory(exp_dir, "template")

        if fail > 0:
            logger.error(f"\n⚠️  发现 {fail} 个无效模板:")
            for file, errs in errors.items():
                logger.error(f"\n  {file}:")
                for err in errs:
                    logger.error(f"    - {err}")

    # 验证知识卡片
    knowledge_dir = Path(config["output"]["knowledge_dir"])
    if knowledge_dir.exists():
        logger.info(f"\n验证知识卡片: {knowledge_dir}")
        success, fail, errors = validate_directory(knowledge_dir, "card")

        if fail > 0:
            logger.error(f"\n⚠️  发现 {fail} 个无效卡片:")
            for file, errs in errors.items():
                logger.error(f"\n  {file}:")
                for err in errs:
                    logger.error(f"    - {err}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="一键导入 chemlab 数据到 VirtualChemLab")

    parser.add_argument("--config", type=str, default=str(TOOL_ROOT / "config.yaml"), help="配置文件路径")

    parser.add_argument("--experiments-only", action="store_true", help="仅导入实验")
    parser.add_argument("--knowledge-only", action="store_true", help="仅导入知识库")

    parser.add_argument("--no-backup", action="store_true", help="不备份现有数据")
    parser.add_argument("--no-validate", action="store_true", help="不验证导入的数据")

    parser.add_argument("--force", action="store_true", help="强制覆盖已存在的文件")
    parser.add_argument("--update", action="store_true", help="更新 chemlab 仓库到最新版本")

    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # 加载配置
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"❌ 配置文件不存在: {config_path}")
        return 1

    config = load_config(config_path)

    # 更新配置
    if args.update:
        config["source"]["auto_update"] = True
    if args.force:
        config["conversion"]["validation"]["strict_mode"] = False

    logger.info("🧪 ChemLab 数据导入工具")
    logger.info(f"配置文件: {config_path}")
    logger.info("")

    # 备份
    if not args.no_backup:
        backup_existing_data(config)

    # 初始化 Fetcher
    fetcher = ChemLabFetcher(config_path)

    try:
        # 克隆/更新仓库
        repo_path = fetcher.clone_or_update()
        logger.info(f"\n📦 仓库路径: {repo_path}")

        repo_info = fetcher.get_repo_info()
        for k, v in repo_info.items():
            logger.info(f"  {k}: {v}")

        # 导入数据
        exp_count = 0
        knowledge_count = 0

        if not args.knowledge_only:
            exp_count = import_experiments(fetcher, config)

        if not args.experiments_only:
            knowledge_count = import_knowledge(fetcher, config)

        # 验证
        if not args.no_validate and config.get("validation", {}).get("validate_on_save", True):
            validate_imported_data(config)

        # 总结
        logger.info("\n" + "=" * 60)
        logger.info("✅ 导入完成!")
        logger.info("=" * 60)
        logger.info(f"实验模板: {exp_count} 个")
        logger.info(f"知识卡片: {knowledge_count} 个")
        logger.info(f"总计: {exp_count + knowledge_count} 个数据文件")

        logger.info("\n下一步:")
        logger.info("  1. 检查生成的文件")
        logger.info("  2. 在 VirtualChemLab 中测试新实验")
        logger.info("  3. 根据需要调整配置和重新导入")

        return 0

    except Exception as e:
        logger.error(f"\n❌ 导入失败: {e}", exc_info=args.verbose)
        return 1

    finally:
        # 可选:清理临时文件
        # fetcher.cleanup()
        pass


if __name__ == "__main__":
    sys.exit(main())
