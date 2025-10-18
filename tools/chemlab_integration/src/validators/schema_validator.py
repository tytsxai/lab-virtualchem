"""数据验证器

使用 Pydantic 模型验证生成的数据。
"""

import logging
import sys
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.models.experiment import ExperimentTemplate
    from src.models.knowledge import KnowledgeCard
except ImportError as e:
    logging.warning(f"无法导入 VirtualChemLab 模型: {e}")
    ExperimentTemplate = None  # type: ignore
    KnowledgeCard = None  # type: ignore

logger = logging.getLogger(__name__)


def validate_template(template_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """验证实验模板

    Args:
        template_data: 模板数据字典

    Returns:
        (是否有效, 错误列表)
    """
    if ExperimentTemplate is None:
        logger.error("ExperimentTemplate 模型未导入,跳过验证")
        return (False, ["模型未导入"])

    errors = []

    try:
        # Pydantic 验证
        ExperimentTemplate(**template_data)
        logger.info(f"✅ 模板验证通过: {template_data.get('id', 'unknown')}")
        return (True, [])

    except ValidationError as e:
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            msg = error["msg"]
            errors.append(f"{field}: {msg}")

        logger.error(f"❌ 模板验证失败: {template_data.get('id', 'unknown')}")
        for err in errors:
            logger.error(f"  - {err}")

        return (False, errors)

    except Exception as e:
        errors.append(f"验证异常: {str(e)}")
        logger.error(f"❌ 验证异常: {e}")
        return (False, errors)


def validate_card(card_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """验证知识卡片

    Args:
        card_data: 卡片数据字典

    Returns:
        (是否有效, 错误列表)
    """
    if KnowledgeCard is None:
        logger.error("KnowledgeCard 模型未导入,跳过验证")
        return (False, ["模型未导入"])

    errors = []

    try:
        # Pydantic 验证
        KnowledgeCard(**card_data)
        logger.info(f"✅ 卡片验证通过: {card_data.get('id', 'unknown')}")
        return (True, [])

    except ValidationError as e:
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            msg = error["msg"]
            errors.append(f"{field}: {msg}")

        logger.error(f"❌ 卡片验证失败: {card_data.get('id', 'unknown')}")
        for err in errors:
            logger.error(f"  - {err}")

        return (False, errors)

    except Exception as e:
        errors.append(f"验证异常: {str(e)}")
        logger.error(f"❌ 验证异常: {e}")
        return (False, errors)


def validate_yaml_file(file_path: Path, data_type: str = "auto") -> tuple[bool, list[str]]:
    """验证 YAML 文件

    Args:
        file_path: 文件路径
        data_type: 数据类型 'template', 'card', 'auto'

    Returns:
        (是否有效, 错误列表)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data_type == "auto":
            # 自动判断类型
            if "steps" in data and "score_rules" in data:
                data_type = "template"
            elif "type" in data and "content" in data:
                data_type = "card"
            else:
                return (False, ["无法自动判断数据类型"])

        if data_type == "template":
            return validate_template(data)
        elif data_type == "card":
            return validate_card(data)
        else:
            return (False, [f"未知数据类型: {data_type}"])

    except yaml.YAMLError as e:
        return (False, [f"YAML 解析错误: {str(e)}"])
    except Exception as e:
        return (False, [f"文件读取错误: {str(e)}"])


def validate_directory(
    directory: Path, data_type: str = "auto", recursive: bool = True
) -> tuple[int, int, dict[str, list[str]]]:
    """验证目录中的所有 YAML 文件

    Args:
        directory: 目录路径
        data_type: 数据类型
        recursive: 是否递归

    Returns:
        (成功数, 失败数, 错误报告)
    """
    directory = Path(directory)
    pattern = "**/*.yaml" if recursive else "*.yaml"
    files = list(directory.glob(pattern))

    success_count = 0
    fail_count = 0
    error_report: dict[str, list[str]] = {}

    logger.info(f"开始验证目录: {directory}")
    logger.info(f"找到 {len(files)} 个 YAML 文件")

    for file_path in files:
        is_valid, errors = validate_yaml_file(file_path, data_type)

        if is_valid:
            success_count += 1
        else:
            fail_count += 1
            error_report[str(file_path)] = errors

    logger.info(f"\n验证完成: ✅ {success_count} 个成功, ❌ {fail_count} 个失败")

    return (success_count, fail_count, error_report)


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 测试数据
    test_template = {
        "id": "test_exp_001",
        "title": "测试实验",
        "level": "basic",
        "duration_min": 45,
        "steps": [{"id": "step_1", "text": "步骤1"}],
    }

    test_card = {
        "id": "test_reagent_001",
        "type": "reagent",
        "title": "测试试剂",
        "content": "这是测试内容",
    }

    print("\n测试模板验证:")
    is_valid, errors = validate_template(test_template)
    print(f"结果: {'✅ 通过' if is_valid else '❌ 失败'}")
    if errors:
        for err in errors:
            print(f"  - {err}")

    print("\n测试卡片验证:")
    is_valid, errors = validate_card(test_card)
    print(f"结果: {'✅ 通过' if is_valid else '❌ 失败'}")
    if errors:
        for err in errors:
            print(f"  - {err}")
