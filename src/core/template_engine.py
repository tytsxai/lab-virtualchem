"""模板引擎 - 加载、解析、验证实验模板"""

import logging
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import Any

import yaml  # type: ignore
from pydantic import ValidationError

from src.models.experiment import ExperimentTemplate
from src.utils.error_handler import safe_execute

from .smart_cache import experiment_cache, template_cache

logger = logging.getLogger(__name__)


class TemplateLoadError(Exception):
    """模板加载错误"""

    def __init__(
        self,
        message: str,
        template_path: Path | None = None,
        details: dict[str, Any] | None = None,
    ):
        """初始化模板加载错误

        Args:
            message: 错误消息
            template_path: 模板文件路径
            details: 额外的错误详情
        """
        self.template_path = template_path
        self.details = details or {}
        full_message = f"{message}"
        if template_path:
            full_message += f" (文件: {template_path.name})"
        super().__init__(full_message)


class TemplateEngine:
    """实验模板引擎"""

    def __init__(self, templates_dir: Path) -> None:
        """初始化模板引擎

        Args:
            templates_dir: 模板目录路径
        """
        self.templates_dir = Path(templates_dir)
        # 使用OrderedDict保证缓存顺序(LRU策略)
        self._templates_cache: OrderedDict[str, ExperimentTemplate] = OrderedDict()
        self._cache_lock = Lock()  # 线程安全的缓存访问
        self._max_cache_size = 50  # 最大缓存数量
        self._load_errors: dict[str, str] = {}  # 记录加载错误的文件
        self._directory_available = True
        try:
            self._cache_namespace = str(self.templates_dir.resolve())
        except Exception:
            self._cache_namespace = str(self.templates_dir)

        if not self.templates_dir.exists():
            logger.warning(f"模板目录不存在: {self.templates_dir}")
            try:
                self.templates_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"已创建模板目录: {self.templates_dir}")
            except Exception as e:
                logger.error(f"创建模板目录失败: {e}")
                self._directory_available = False

    @safe_execute(context="加载实验模板", raise_error=True)
    def load_experiment(self, template_path: Path) -> ExperimentTemplate:
        """加载实验模板

        Args:
            template_path: 模板文件路径

        Returns:
            验证后的实验模板对象

        Raises:
            TemplateLoadError: 模板加载失败
            ValidationError: 模板格式错误
        """
        # 验证文件存在
        template_path = Path(template_path)
        if not template_path.exists():
            raise TemplateLoadError(f"模板文件不存在: {template_path}")

        if not template_path.is_file():
            raise TemplateLoadError(f"路径不是文件: {template_path}")

        # 验证文件大小(防止加载过大文件)
        max_size = 10 * 1024 * 1024  # 10MB
        if template_path.stat().st_size > max_size:
            raise TemplateLoadError(
                f"模板文件过大: {template_path.stat().st_size} bytes"
            )

        try:
            # 读取YAML文件
            with open(template_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data:
                raise TemplateLoadError("模板文件为空或内容无效", template_path)

            if not isinstance(data, dict):
                raise TemplateLoadError(
                    f"模板根节点必须是字典类型，当前类型: {type(data).__name__}",
                    template_path,
                )

            if "experiment" not in data:
                available_keys = ", ".join(data.keys()) if data else "无"
                raise TemplateLoadError(
                    f"模板缺少 'experiment' 根节点，可用键: {available_keys}",
                    template_path,
                )

            # 验证并创建模板对象
            experiment_data = data["experiment"]

            if not isinstance(experiment_data, dict):
                raise TemplateLoadError(
                    f"experiment 节点必须是字典类型，当前类型: {type(experiment_data).__name__}",
                    template_path,
                )

            # 处理score字段(兼容旧格式)
            if "score" in experiment_data and "rules" in experiment_data["score"]:
                experiment_data["score_rules"] = experiment_data["score"]["rules"]
                del experiment_data["score"]
                logger.debug(f"已转换旧格式评分规则: {template_path.name}")

            # 验证必需字段
            required_fields = ["id", "title", "steps"]
            missing_fields = [
                field for field in required_fields if field not in experiment_data
            ]
            if missing_fields:
                raise TemplateLoadError(
                    f"模板缺少必需字段: {', '.join(missing_fields)}",
                    template_path,
                    {"missing_fields": missing_fields},
                )

            # 兼容旧版/简化版模板格式，将简单的 inputs + validation_rules
            # 转换为 ExperimentTemplate/Step 所需的 check 结构
            steps = experiment_data.get("steps")
            if isinstance(steps, list):
                normalized_steps: list[dict[str, Any]] = []
                for raw_step in steps:
                    # 仅处理字典类型的步骤定义
                    if not isinstance(raw_step, dict):
                        normalized_steps.append(raw_step)
                        continue

                    step_data = dict(raw_step)

                    # 已经有 check 的按照新格式处理，不再转换
                    if "check" not in step_data:
                        validation_rules = step_data.get("validation_rules") or []
                        inputs = step_data.get("inputs") or []

                        # 仅处理最常见的简单场景：单个数值输入 + 单个 range 规则
                        if (
                            isinstance(validation_rules, list)
                            and validation_rules
                            and isinstance(inputs, list)
                            and inputs
                        ):
                            first_rule = validation_rules[0]
                            first_input = inputs[0]

                            try:
                                rule_type = first_rule.get("type")
                                if rule_type == "range":
                                    # 从输入定义中推断 key/label/unit
                                    key = (
                                        first_input.get("id")
                                        or first_input.get("key")
                                        or first_rule.get("field")
                                    )
                                    if key:
                                        label = first_input.get("label", key)
                                        unit = first_input.get("unit")

                                        min_val = first_rule.get("min")
                                        max_val = first_rule.get("max")
                                        range_spec: list[float] | None = None
                                        if min_val is not None and max_val is not None:
                                            range_spec = [
                                                float(min_val),
                                                float(max_val),
                                            ]

                                        input_spec: dict[str, Any] = {
                                            "key": key,
                                            "label": label,
                                            "input_type": "float",
                                            "range": range_spec,
                                            "unit": unit,
                                        }

                                        step_data["check"] = {
                                            "type": "input",
                                            "input": input_spec,
                                            "correct_value": step_data.get(
                                                "correct_value"
                                            ),
                                            "fail_hint": first_rule.get(
                                                "error_message", "输入值超出允许范围"
                                            ),
                                        }
                            except Exception as e:  # noqa: BLE001
                                # 不影响其它模板加载，只记录日志
                                logger.debug(f"旧版步骤格式转换失败，保持原样: {e}")

                    normalized_steps.append(step_data)

                experiment_data["steps"] = normalized_steps

            template = ExperimentTemplate(**experiment_data)

            # 验证依赖关系
            errors = template.validate_dependencies()
            if errors:
                raise TemplateLoadError(
                    f"依赖关系验证失败: {'; '.join(errors)}",
                    template_path,
                    {"dependency_errors": errors},
                )

            # 线程安全地缓存模板
            with self._cache_lock:
                # 检查缓存大小，使用LRU策略
                if len(self._templates_cache) >= self._max_cache_size:
                    # OrderedDict会保持插入顺序，移除最早的项
                    first_key, _ = self._templates_cache.popitem(last=False)
                    logger.debug(f"缓存已满，移除最早项: {first_key}")

                # 如果ID已存在，先移除再添加(更新LRU顺序)
                if template.id in self._templates_cache:
                    del self._templates_cache[template.id]

                self._templates_cache[template.id] = template

            # 清除之前的错误记录
            if str(template_path) in self._load_errors:
                del self._load_errors[str(template_path)]

            logger.info(
                f"成功加载模板: {template.id} - {template.title} (文件: {template_path.name})"
            )
            return template

        except yaml.YAMLError as e:
            error_msg = f"YAML解析错误: {e}"
            self._load_errors[str(template_path)] = error_msg
            raise TemplateLoadError(
                error_msg, template_path, {"yaml_error": str(e)}
            ) from e
        except ValidationError as e:
            error_msg = f"模板格式验证失败: {len(e.errors())} 个错误"
            self._load_errors[str(template_path)] = error_msg
            logger.error(f"模板验证失败 {template_path.name}: {e}")
            raise TemplateLoadError(
                error_msg,
                template_path,
                {"validation_errors": [err["msg"] for err in e.errors()]},
            ) from e
        except TemplateLoadError:
            # 已经是我们的错误类型，直接抛出
            raise
        except Exception as e:
            error_msg = f"加载失败: {type(e).__name__}: {e}"
            self._load_errors[str(template_path)] = error_msg
            logger.error(f"加载模板时发生未知错误: {e}", exc_info=True)
            raise TemplateLoadError(
                error_msg, template_path, {"exception_type": type(e).__name__}
            ) from e

    def load_experiment_by_id(self, experiment_id: str) -> ExperimentTemplate:
        """根据ID加载实验模板

        Args:
            experiment_id: 实验ID (可以是文件名或模板内的ID)

        Returns:
            实验模板对象

        Raises:
            TemplateLoadError: 模板加载失败
        """
        if not experiment_id or not experiment_id.strip():
            raise TemplateLoadError("实验ID不能为空")

        experiment_id = experiment_id.strip()

        # 先尝试从智能缓存获取
        cached_template = template_cache.get_template(experiment_id)
        if cached_template is not None:
            logger.debug(f"从智能缓存加载模板: {experiment_id}")
            return cached_template

        # 再检查本地缓存(线程安全)，并更新LRU顺序
        with self._cache_lock:
            if experiment_id in self._templates_cache:
                logger.debug(f"从本地缓存加载模板: {experiment_id}")
                # 更新访问顺序 (move_to_end将其移到末尾，表示最近使用)
                self._templates_cache.move_to_end(experiment_id)
                template = self._templates_cache[experiment_id]
                # 同时更新智能缓存
                template_cache.set_template(experiment_id, template)
                return template

        # 在模板目录中查找
        template_path = self.templates_dir / f"{experiment_id}.yaml"
        if not template_path.exists():
            # 尝试其他可能的文件名格式
            alternative_path = self.templates_dir / f"{experiment_id}.yml"
            if alternative_path.exists():
                template_path = alternative_path
            else:
                # 如果直接按文件名找不到，遍历所有模板文件查找匹配的ID
                found = False
                if self.templates_dir.exists():
                    for yaml_file in self.templates_dir.glob("*.yaml"):
                        try:
                            with open(yaml_file, encoding="utf-8") as f:
                                data = yaml.safe_load(f)
                            if (
                                data
                                and "experiment" in data
                                and data["experiment"].get("id") == experiment_id
                            ):
                                template_path = yaml_file
                                found = True
                                logger.debug(
                                    f"通过ID匹配找到模板文件: {yaml_file.name}"
                                )
                                break
                        except Exception:
                            continue

                if not found:
                    raise TemplateLoadError(
                        f"找不到实验模板: {experiment_id} (搜索路径: {self.templates_dir})"
                    )

        return self.load_experiment(template_path)

    def list_available_experiments(self) -> list[dict[str, str]]:
        """列出所有可用实验

        Returns:
            实验列表 [{"id": "...", "title": "...", "level": "..."}, ...]
        """
        if not self._directory_available:
            return []

        # 先尝试从智能缓存获取
        cached_experiments = experiment_cache.get_experiment_list(
            namespace=self._cache_namespace
        )
        if cached_experiments is not None:
            logger.debug("从智能缓存加载实验列表")
            return cached_experiments

        experiments: list[dict[str, str]] = []

        if not self.templates_dir.exists():
            return experiments

        for template_file in self.templates_dir.glob("*.yaml"):
            try:
                template = self.load_experiment(template_file)
                experiments.append(
                    {
                        "id": template.id,
                        "title": template.title,
                        "title_en": template.title_en or "",
                        "level": template.level,
                        "duration_min": str(template.duration_min),
                        "version": template.version,
                    }
                )
            except Exception as e:
                logger.error(f"加载模板失败 {template_file}: {e}")
                continue

        sorted_experiments = sorted(experiments, key=lambda x: x["level"])

        # 缓存实验结果
        experiment_cache.set_experiment_list(
            sorted_experiments, namespace=self._cache_namespace
        )

        return sorted_experiments

    def validate_template(self, template_path: Path) -> tuple[bool, list[str]]:
        """验证模板格式

        Args:
            template_path: 模板文件路径

        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []

        try:
            template = self.load_experiment(template_path)

            # 额外的业务逻辑验证
            if not template.steps:
                errors.append("模板验证失败: 实验必须至少包含一个步骤")

            if not template.goals:
                errors.append("建议设置实验目标")

            # 验证曲线参数完整性
            for curve in template.curves:
                if curve.type.value == "titration_ph":
                    required_params = ["acid_M", "acid_V_ml", "base_M"]
                    for param in required_params:
                        if param not in curve.params:
                            errors.append(f"曲线 {curve.id} 缺少参数: {param}")

            return len(errors) == 0, errors

        except Exception as e:
            errors.append(f"验证模板时发生错误: {e}")
            return False, errors

    def save_template(self, template: ExperimentTemplate, output_path: Path) -> None:
        """保存模板到文件

        Args:
            template: 实验模板对象
            output_path: 输出文件路径
        """
        import yaml

        # 转换为字典格式
        template_dict = template.model_dump()

        # 包装在experiment键下（与YAML文件格式一致）
        yaml_data = {"experiment": template_dict}

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入YAML文件
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(
                yaml_data, f, default_flow_style=False, allow_unicode=True, indent=2
            )

        logger.info(f"模板已保存: {output_path}")

    def get_template_info(self, experiment_id: str) -> dict[str, str]:
        """获取模板基本信息(不完全加载)

        Args:
            experiment_id: 实验ID

        Returns:
            模板信息字典
        """
        template_path = self.templates_dir / f"{experiment_id}.yaml"

        if not template_path.exists():
            return {}

        try:
            with open(template_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data or "experiment" not in data:
                return {}

            exp_data = data["experiment"]
            return {
                "id": exp_data.get("id", ""),
                "title": exp_data.get("title", ""),
                "level": exp_data.get("level", "basic"),
                "duration_min": str(exp_data.get("duration_min", 45)),
            }

        except Exception as e:
            logger.error(f"读取模板信息失败: {e}")
            return {}

    def clear_cache(self) -> None:
        """清空模板缓存"""
        with self._cache_lock:
            self._templates_cache.clear()
            self._load_errors.clear()
        logger.info("模板缓存已清空")

    def get_cache_info(self) -> dict[str, Any]:
        """获取缓存信息

        Returns:
            缓存统计信息
        """
        with self._cache_lock:
            return {
                "cache_size": len(self._templates_cache),
                "max_cache_size": self._max_cache_size,
                "cached_ids": list(self._templates_cache.keys()),
                "load_errors_count": len(self._load_errors),
                "cache_utilization": f"{len(self._templates_cache) / self._max_cache_size * 100:.1f}%",
            }

    def health_check(self) -> dict[str, Any]:
        """健康检查

        Returns:
            健康检查结果，包含状态和详情
        """
        result = {
            "status": "healthy",
            "templates_dir_exists": self.templates_dir.exists(),
            "templates_dir_writable": False,
            "template_count": 0,
            "valid_templates": 0,
            "invalid_templates": 0,
            "cache_info": self.get_cache_info(),
            "errors": [],
        }

        # 检查目录写入权限
        try:
            test_file = self.templates_dir / ".health_check"
            test_file.touch()
            test_file.unlink()
            result["templates_dir_writable"] = True
        except Exception as e:
            result["errors"].append(f"目录不可写: {e}")
            result["status"] = "warning"

        # 检查模板文件
        if self.templates_dir.exists():
            template_files = list(self.templates_dir.glob("*.yaml"))
            result["template_count"] = len(template_files)

            for template_file in template_files:
                try:
                    # 尝试加载（会使用缓存）
                    self.load_experiment(template_file)
                    result["valid_templates"] += 1
                except Exception as e:
                    result["invalid_templates"] += 1
                    result["errors"].append(f"{template_file.name}: {str(e)}")

            if result["invalid_templates"] > 0:
                result["status"] = (
                    "degraded" if result["valid_templates"] > 0 else "unhealthy"
                )

        return result

    def repair_templates(self, dry_run: bool = True) -> dict[str, Any]:
        """尝试修复有问题的模板

        Args:
            dry_run: 如果为True，只检测不修复

        Returns:
            修复结果报告
        """
        report = {
            "checked": 0,
            "repairable": 0,
            "repaired": 0,
            "failed": 0,
            "issues": [],
        }

        if not self.templates_dir.exists():
            report["issues"].append("模板目录不存在")
            return report

        for template_file in self.templates_dir.glob("*.yaml"):
            report["checked"] += 1

            try:
                # 尝试加载
                self.load_experiment(template_file)
            except TemplateLoadError as e:
                # 分析错误类型
                if "缺少必需字段" in str(e):
                    report["repairable"] += 1
                    issue = {
                        "file": template_file.name,
                        "type": "missing_fields",
                        "details": e.details,
                        "repairable": True,
                    }
                    report["issues"].append(issue)

                    if not dry_run:
                        # 尝试自动修复
                        repaired = self._repair_template(template_file, e.details)
                        if repaired:
                            report["repaired"] += 1
                            logger.info(f"已修复模板: {template_file.name}")
                        else:
                            logger.warning(f"无法自动修复: {template_file.name}")
                else:
                    report["failed"] += 1
                    issue = {
                        "file": template_file.name,
                        "type": "other_error",
                        "error": str(e),
                        "repairable": False,
                    }
                    report["issues"].append(issue)

        return report

    def get_load_errors(self) -> dict[str, str]:
        """获取加载错误记录

        Returns:
            文件路径到错误消息的映射
        """
        return self._load_errors.copy()

    def _repair_template(
        self, template_file: Path, _missing_fields: dict[str, Any]
    ) -> bool:
        """自动修复模板文件

        Args:
            template_file: 模板文件路径
            missing_fields: 缺失的字段信息

        Returns:
            是否修复成功
        """
        try:
            import shutil

            import yaml

            # 备份原文件
            backup_file = template_file.with_suffix(".yaml.bak")
            shutil.copy2(template_file, backup_file)
            logger.info(f"已备份原模板: {backup_file}")

            # 加载原模板数据
            with open(template_file, encoding="utf-8") as f:
                template_data = yaml.safe_load(f)

            if not isinstance(template_data, dict):
                logger.error("模板数据格式不正确")
                return False

            # 修复缺失的字段
            repaired = False

            # 1. 补充基础信息字段
            if "id" not in template_data or not template_data["id"]:
                template_data["id"] = template_file.stem
                repaired = True
                logger.info(f"补充ID字段: {template_data['id']}")

            if "title" not in template_data or not template_data["title"]:
                template_data["title"] = template_file.stem.replace("_", " ").title()
                repaired = True
                logger.info(f"补充标题字段: {template_data['title']}")

            if "description" not in template_data:
                template_data["description"] = (
                    f"{template_data.get('title', '实验')}的详细说明"
                )
                repaired = True

            if "level" not in template_data:
                template_data["level"] = "intermediate"
                repaired = True

            if "duration_minutes" not in template_data:
                # 根据步骤数估算时长
                steps = template_data.get("steps", [])
                template_data["duration_minutes"] = max(30, len(steps) * 5)
                repaired = True

            # 2. 确保有steps字段
            if "steps" not in template_data:
                template_data["steps"] = []
                repaired = True
                logger.warning("步骤列表为空，已添加空列表")

            # 3. 修复步骤数据
            if isinstance(template_data.get("steps"), list):
                for i, step in enumerate(template_data["steps"]):
                    if not isinstance(step, dict):
                        continue

                    step_modified = False

                    if "id" not in step or not step["id"]:
                        step["id"] = f"step_{i + 1}"
                        step_modified = True

                    if "content" not in step or not step["content"]:
                        step["content"] = f"步骤 {i + 1}"
                        step_modified = True

                    if "type" not in step:
                        step["type"] = "operation"
                        step_modified = True

                    if step_modified:
                        repaired = True

            # 4. 添加默认的标签和分类
            if "tags" not in template_data:
                template_data["tags"] = ["实验", "化学"]
                repaired = True

            if "category" not in template_data:
                template_data["category"] = "general"
                repaired = True

            # 5. 添加学习目标
            if "objectives" not in template_data:
                template_data["objectives"] = [
                    "理解实验原理",
                    "掌握实验操作",
                    "学会数据分析",
                ]
                repaired = True

            # 如果有修复，保存文件
            if repaired:
                with open(template_file, "w", encoding="utf-8") as f:
                    yaml.safe_dump(
                        template_data,
                        f,
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=False,
                    )
                logger.info(f"已保存修复后的模板: {template_file}")
                return True
            else:
                logger.info("没有需要修复的内容")
                # 删除备份文件
                backup_file.unlink()
                return False

        except Exception as e:
            logger.error(f"修复模板失败: {e}", exc_info=True)
            # 尝试恢复备份
            if backup_file.exists():
                try:
                    shutil.copy2(backup_file, template_file)
                    logger.info("已从备份恢复原模板")
                except Exception:
                    pass
            return False
