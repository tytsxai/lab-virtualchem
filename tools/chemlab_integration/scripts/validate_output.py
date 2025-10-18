#!/usr/bin/env python3
"""验证输出数据

验证导入的实验模板和知识卡片是否符合 VirtualChemLab 标准。
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import colorlog

# 添加项目路径
TOOL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(TOOL_ROOT))

from src.validators.schema_validator import validate_directory  # noqa: E402

# 配置彩色日志
handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(message)s",
        log_colors={"DEBUG": "cyan", "INFO": "green", "WARNING": "yellow", "ERROR": "red", "CRITICAL": "red,bg_white"},
    )
)

logger = colorlog.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="验证 VirtualChemLab 数据文件")

    parser.add_argument("path", type=str, help="要验证的文件或目录路径")

    parser.add_argument("--type", type=str, choices=["template", "card", "auto"], default="auto", help="数据类型")

    parser.add_argument("--output", type=str, help="保存错误报告到 JSON 文件")

    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    target_path = Path(args.path)

    if not target_path.exists():
        logger.error(f"❌ 路径不存在: {target_path}")
        return 1

    logger.info(f"🔍 验证: {target_path}")
    logger.info(f"类型: {args.type}\n")

    if target_path.is_file():
        # 验证单个文件
        from src.validators.schema_validator import validate_yaml_file

        is_valid, errors = validate_yaml_file(target_path, args.type)

        if is_valid:
            logger.info("✅ 验证通过")
            return 0
        else:
            logger.error("❌ 验证失败:")
            for err in errors:
                logger.error(f"  - {err}")
            return 1

    else:
        # 验证目录
        success, fail, error_report = validate_directory(target_path, args.type)

        # 保存报告
        if args.output and error_report:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(error_report, f, indent=2, ensure_ascii=False)

            logger.info(f"\n📄 错误报告已保存到: {output_path}")

        # 返回状态
        if fail == 0:
            logger.info("\n✅ 所有文件验证通过!")
            return 0
        else:
            logger.error(f"\n❌ 发现 {fail} 个无效文件")
            return 1


if __name__ == "__main__":
    import logging

    sys.exit(main())
