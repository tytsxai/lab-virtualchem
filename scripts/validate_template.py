"""模板验证工具"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import argparse  # noqa: E402

from src.core.template_engine import TemplateEngine  # noqa: E402
from src.utils.logger import setup_logger  # noqa: E402

logger = setup_logger("template_validator")


def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(description="验证实验模板格式")
    parser.add_argument("template_path", type=Path, help="模板文件路径")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")

    args = parser.parse_args()

    if not args.template_path.exists():
        logger.error(f"文件不存在: {args.template_path}")
        return 1

    # 创建模板引擎
    engine = TemplateEngine(args.template_path.parent)

    # 验证模板
    logger.info(f"验证模板: {args.template_path}")
    valid, errors = engine.validate_template(args.template_path)

    if valid:
        logger.info("✓ 模板验证通过!")

        if args.verbose:
            # 加载并显示模板信息
            try:
                template = engine.load_experiment(args.template_path)
                logger.info("\n模板信息:")
                logger.info(f"  ID: {template.id}")
                logger.info(f"  标题: {template.title}")
                logger.info(f"  难度: {template.level}")
                logger.info(f"  步骤数: {len(template.steps)}")
                logger.info(f"  曲线数: {len(template.curves)}")
                logger.info(f"  评分规则: {len(template.score_rules)}")
            except Exception as e:
                logger.error(f"加载模板失败: {e}")
                return 1

        return 0
    else:
        logger.error("✗ 模板验证失败!")
        for error in errors:
            logger.error(f"  - {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())




