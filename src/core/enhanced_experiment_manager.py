"""增强的实验管理器 - 支持动态加载、热重载、版本兼容

主要功能:
1. 实验模板的动态加载和热重载
2. 多版本兼容性支持
3. 实验状态持久化和恢复
4. 实验依赖关系管理
5. 批量实验操作
6. 实验模板迁移和升级
"""

import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from threading import Lock, RLock
from typing import Any

from ..ai.experiment_compiler import ExperimentCompiler, compile_experiment
from ..core.experiment_controller import ExperimentController
from ..core.template_engine import TemplateEngine, TemplateLoadError
from ..models.experiment import ExperimentTemplate
from ..models.user_record import UserRecord

logger = logging.getLogger(__name__)


class ExperimentNotFoundError(Exception):
    """实验未找到错误"""

    pass


class ExperimentManagerError(Exception):
    """实验管理器错误"""

    pass


class EnhancedExperimentManager:
    """增强的实验管理器"""

    def __init__(
        self,
        templates_dir: Path | str,
        records_dir: Path | str | None = None,
        ai_assistant: Any = None,
    ) -> None:
        """初始化实验管理器

        Args:
            templates_dir: 模板目录
            records_dir: 记录保存目录
            ai_assistant: AI助手实例(可选)
        """
        self.templates_dir = Path(templates_dir)
        self.records_dir = Path(records_dir) if records_dir else Path("data/records")

        # 确保目录存在
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.records_dir.mkdir(parents=True, exist_ok=True)

        # 初始化模板引擎
        self.template_engine = TemplateEngine(self.templates_dir)

        # 初始化编译器
        self.compiler = ExperimentCompiler(ai_assistant=ai_assistant)

        # 活动的实验控制器 {session_id: controller}
        self._active_sessions: dict[str, ExperimentController] = {}
        self._sessions_lock = Lock()

        # 实验依赖关系图 {experiment_id: [prerequisite_ids]}
        self._dependency_graph: dict[str, list[str]] = {}
        self._graph_lock = RLock()

        # 实验分类索引 {category: [experiment_ids]}
        self._category_index: dict[str, list[str]] = defaultdict(list)
        self._index_lock = Lock()

        # 模板文件监控
        self._file_timestamps: dict[str, float] = {}

        # 初始化索引
        self._rebuild_indices()

        logger.info(f"实验管理器已初始化: {self.templates_dir}")

    def load_experiment(self, experiment_id: str, force_reload: bool = False) -> ExperimentTemplate:
        """加载实验模板

        Args:
            experiment_id: 实验ID
            force_reload: 是否强制重新加载

        Returns:
            实验模板

        Raises:
            ExperimentNotFoundError: 实验不存在
        """
        try:
            if force_reload:
                # 清除缓存
                self.template_engine.clear_cache()

            template = self.template_engine.load_experiment_by_id(experiment_id)

            # 更新索引
            self._update_indices(template)

            return template

        except TemplateLoadError as e:
            raise ExperimentNotFoundError(f"加载实验失败: {e}") from e

    def add_experiment(
        self,
        source: str | dict[str, Any] | Path,
        format_type: str = "auto",
        save: bool = True,
    ) -> tuple[bool, ExperimentTemplate | None, list[str]]:
        """添加新实验

        Args:
            source: 实验数据源
            format_type: 格式类型
            save: 是否保存到文件

        Returns:
            (是否成功, 实验模板, 错误/警告信息)
        """
        messages: list[str] = []

        try:
            # 编译实验
            result = compile_experiment(source, format_type=format_type, ai_assistant=self.compiler.ai_assistant)

            if not result.success:
                if result.errors:
                    messages.extend(result.errors)
                return False, None, messages

            template = result.template
            if result.warnings:
                messages.extend(result.warnings)

            # 检查模板是否为None
            if template is None:
                messages.append("错误: 编译失败，模板为空")
                return False, None, messages

            # 检查ID冲突
            if self._experiment_exists(template.id):
                messages.append(f"警告: 实验ID {template.id} 已存在，将覆盖")

            # 验证依赖
            if template.prerequisites:
                for prereq_id in template.prerequisites:
                    if not self._experiment_exists(prereq_id):
                        messages.append(f"警告: 前置实验 {prereq_id} 不存在")

            # 保存到文件
            if save:
                save_path = self.templates_dir / f"{template.id}.yaml"
                if self._save_template(template, save_path):
                    messages.append(f"实验已保存至: {save_path.name}")
                else:
                    messages.append("警告: 保存失败")

            # 更新缓存和索引
            self.template_engine.clear_cache()
            self.template_engine.load_experiment_by_id(template.id)
            self._update_indices(template)

            logger.info(f"成功添加实验: {template.id}")

            return True, template, messages

        except Exception as e:
            messages.append(f"添加实验失败: {e}")
            logger.error(f"添加实验失败: {e}", exc_info=True)
            return False, None, messages

    def update_experiment(self, experiment_id: str, updates: dict[str, Any]) -> tuple[bool, list[str]]:
        """更新实验

        Args:
            experiment_id: 实验ID
            updates: 更新数据

        Returns:
            (是否成功, 消息列表)
        """
        messages: list[str] = []

        try:
            # 加载现有模板
            template = self.load_experiment(experiment_id)

            # 应用更新
            template_dict = template.model_dump()
            template_dict.update(updates)

            # 重新编译
            result = self.compiler.compile_from_dict(template_dict)

            if not result.success or result.template is None:
                if result.errors:
                    messages.extend(result.errors)
                return False, messages

            # 保存
            save_path = self.templates_dir / f"{experiment_id}.yaml"
            if self._save_template(result.template, save_path):
                messages.append("实验更新成功")

                # 重新加载
                self.load_experiment(experiment_id, force_reload=True)

                return True, messages
            else:
                messages.append("保存失败")
                return False, messages

        except Exception as e:
            messages.append(f"更新失败: {e}")
            logger.error(f"更新实验失败: {e}", exc_info=True)
            return False, messages

    def delete_experiment(self, experiment_id: str, force: bool = False) -> tuple[bool, list[str]]:
        """删除实验

        Args:
            experiment_id: 实验ID
            force: 是否强制删除(即使有依赖)

        Returns:
            (是否成功, 消息列表)
        """
        messages = []

        try:
            # 检查是否存在
            if not self._experiment_exists(experiment_id):
                messages.append(f"实验 {experiment_id} 不存在")
                return False, messages

            # 检查依赖
            dependent_experiments = self._get_dependent_experiments(experiment_id)
            if dependent_experiments and not force:
                messages.append(f"以下实验依赖于 {experiment_id}: {', '.join(dependent_experiments)}")
                messages.append("使用 force=True 强制删除")
                return False, messages

            # 删除文件
            template_file = self.templates_dir / f"{experiment_id}.yaml"
            if template_file.exists():
                template_file.unlink()
                messages.append(f"已删除模板文件: {template_file.name}")

            # 清除缓存和索引
            self.template_engine.clear_cache()
            self._rebuild_indices()

            logger.info(f"已删除实验: {experiment_id}")

            return True, messages

        except Exception as e:
            messages.append(f"删除失败: {e}")
            logger.error(f"删除实验失败: {e}", exc_info=True)
            return False, messages

    def list_experiments(
        self,
        category: str | None = None,
        level: str | None = None,
        _include_disabled: bool = False,
    ) -> list[dict[str, Any]]:
        """列出实验

        Args:
            category: 分类筛选
            level: 难度筛选
            include_disabled: 是否包含禁用的实验

        Returns:
            实验列表
        """
        experiments = self.template_engine.list_available_experiments()

        # 应用筛选
        if category:
            experiments = [exp for exp in experiments if exp.get("category") == category]

        if level:
            experiments = [exp for exp in experiments if exp.get("level") == level]

        return experiments

    def get_experiment_info(self, experiment_id: str) -> dict[str, Any]:
        """获取实验详细信息

        Args:
            experiment_id: 实验ID

        Returns:
            实验信息
        """
        try:
            template = self.load_experiment(experiment_id)

            return {
                "id": template.id,
                "title": template.title,
                "title_en": template.title_en,
                "description": template.description,
                "category": template.category,
                "level": template.level,
                "duration_min": template.duration_min,
                "steps_count": len(template.steps),
                "reagents_count": len(template.reagents),
                "prerequisites": template.prerequisites,
                "version": template.version,
                "has_curves": len(template.curves) > 0,
                "has_goals": len(template.goals) > 0,
            }

        except Exception as e:
            logger.error(f"获取实验信息失败: {e}")
            return {}

    def start_experiment_session(self, experiment_id: str, user_id: str) -> tuple[str, ExperimentController]:
        """开始实验会话

        Args:
            experiment_id: 实验ID
            user_id: 用户ID

        Returns:
            (会话ID, 实验控制器)

        Raises:
            ExperimentNotFoundError: 实验不存在
        """
        try:
            # 加载模板
            template = self.load_experiment(experiment_id)

            # 创建控制器
            controller = ExperimentController(template, user_id)
            controller.start_experiment()

            # 生成会话ID
            session_id = f"{user_id}_{experiment_id}_{datetime.now().timestamp()}"

            # 保存会话
            with self._sessions_lock:
                self._active_sessions[session_id] = controller

            logger.info(f"实验会话已创建: {session_id}")

            return session_id, controller

        except Exception as e:
            raise ExperimentManagerError(f"启动实验会话失败: {e}") from e

    def get_session(self, session_id: str) -> ExperimentController | None:
        """获取实验会话

        Args:
            session_id: 会话ID

        Returns:
            实验控制器或None
        """
        with self._sessions_lock:
            return self._active_sessions.get(session_id)

    def end_experiment_session(self, session_id: str, save_record: bool = True) -> UserRecord | None:
        """结束实验会话

        Args:
            session_id: 会话ID
            save_record: 是否保存记录

        Returns:
            用户记录或None
        """
        with self._sessions_lock:
            controller = self._active_sessions.get(session_id)

            if not controller:
                logger.warning(f"会话不存在: {session_id}")
                return None

            try:
                # 完成实验
                record = controller.complete_experiment()

                # 保存记录
                if save_record:
                    self._save_record(record)

                # 移除会话
                del self._active_sessions[session_id]

                logger.info(f"实验会话已结束: {session_id}")

                return record

            except Exception as e:
                logger.error(f"结束实验会话失败: {e}", exc_info=True)
                return None

    def list_active_sessions(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """列出活动会话

        Args:
            user_id: 用户ID筛选(可选)

        Returns:
            会话列表
        """
        sessions = []

        with self._sessions_lock:
            for session_id, controller in self._active_sessions.items():
                if user_id and controller.user_id != user_id:
                    continue

                sessions.append(
                    {
                        "session_id": session_id,
                        "user_id": controller.user_id,
                        "experiment_id": controller.template.id,
                        "experiment_title": controller.template.title,
                        "progress": controller.get_progress(),
                    }
                )

        return sessions

    def check_prerequisites(self, experiment_id: str, user_id: str) -> tuple[bool, list[str]]:
        """检查用户是否满足实验前置条件

        Args:
            experiment_id: 实验ID
            user_id: 用户ID

        Returns:
            (是否满足, 缺少的前置实验列表)
        """
        try:
            template = self.load_experiment(experiment_id)

            if not template.prerequisites:
                return True, []

            # 获取用户完成的实验
            completed_experiments = self._get_user_completed_experiments(user_id)

            # 检查前置实验
            missing = [prereq for prereq in template.prerequisites if prereq not in completed_experiments]

            return len(missing) == 0, missing

        except Exception as e:
            logger.error(f"检查前置条件失败: {e}")
            return False, []

    def get_experiment_statistics(self) -> dict[str, Any]:
        """获取实验统计信息

        Returns:
            统计信息
        """
        experiments = self.list_experiments()

        stats = {
            "total_experiments": len(experiments),
            "by_level": defaultdict(int),
            "by_category": defaultdict(int),
            "active_sessions": len(self._active_sessions),
            "total_records": self._count_records(),
        }

        for exp in experiments:
            level_key = exp.get("level", "unknown")
            category_key = exp.get("category", "uncategorized")
            level_dict = dict(stats["by_level"])
            category_dict = dict(stats["by_category"])
            level_dict[level_key] = level_dict.get(level_key, 0) + 1
            category_dict[category_key] = category_dict.get(category_key, 0) + 1
            stats["by_level"] = level_dict
            stats["by_category"] = category_dict

        return dict(stats)

    def check_for_updates(self) -> list[str]:
        """检查模板文件更新

        Returns:
            已更新的实验ID列表
        """
        updated = []

        try:
            for template_file in self.templates_dir.glob("*.yaml"):
                current_mtime = template_file.stat().st_mtime
                stored_mtime = self._file_timestamps.get(str(template_file), 0)

                if current_mtime > stored_mtime:
                    # 文件已更新
                    self._file_timestamps[str(template_file)] = current_mtime

                    # 尝试获取实验ID
                    try:
                        import yaml

                        with open(template_file, encoding="utf-8") as f:
                            data = yaml.safe_load(f)
                        if data and "experiment" in data:
                            exp_id = data["experiment"].get("id")
                            if exp_id:
                                updated.append(exp_id)
                                logger.info(f"检测到实验更新: {exp_id}")
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"检查更新失败: {e}")

        return updated

    def reload_updated_experiments(self) -> int:
        """重新加载已更新的实验

        Returns:
            重新加载的实验数量
        """
        updated = self.check_for_updates()

        count = 0
        for exp_id in updated:
            try:
                self.load_experiment(exp_id, force_reload=True)
                count += 1
            except Exception as e:
                logger.error(f"重新加载实验失败 {exp_id}: {e}")

        if count > 0:
            logger.info(f"已重新加载 {count} 个实验")

        return count

    def _experiment_exists(self, experiment_id: str) -> bool:
        """检查实验是否存在"""
        template_file = self.templates_dir / f"{experiment_id}.yaml"
        return template_file.exists()

    def _save_template(self, template: ExperimentTemplate, output_path: Path) -> bool:
        """保存模板到文件"""
        try:
            import yaml

            template_dict = {"experiment": template.model_dump(exclude_none=True)}

            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    template_dict,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            return True

        except Exception as e:
            logger.error(f"保存模板失败: {e}", exc_info=True)
            return False

    def _save_record(self, record: UserRecord) -> bool:
        """保存用户记录"""
        try:
            user_dir = self.records_dir / record.user_id
            user_dir.mkdir(parents=True, exist_ok=True)

            record_file = user_dir / f"{record.record_id}.json"

            with open(record_file, "w", encoding="utf-8") as f:
                json.dump(record.model_dump(), f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"记录已保存: {record_file}")
            return True

        except Exception as e:
            logger.error(f"保存记录失败: {e}", exc_info=True)
            return False

    def _get_user_completed_experiments(self, user_id: str) -> set[str]:
        """获取用户完成的实验列表"""
        completed: set[str] = set()

        try:
            user_dir = self.records_dir / user_id

            if not user_dir.exists():
                return completed

            for record_file in user_dir.glob("*.json"):
                try:
                    with open(record_file, encoding="utf-8") as f:
                        data = json.load(f)

                    if data.get("status") == "completed":
                        completed.add(data.get("experiment_id"))

                except Exception:
                    pass

        except Exception as e:
            logger.error(f"获取用户记录失败: {e}")

        return completed

    def _count_records(self) -> int:
        """统计记录数量"""
        count = 0

        try:
            for user_dir in self.records_dir.iterdir():
                if user_dir.is_dir():
                    count += len(list(user_dir.glob("*.json")))
        except Exception:
            pass

        return count

    def _rebuild_indices(self) -> None:
        """重建索引"""
        with self._index_lock, self._graph_lock:
            self._category_index.clear()
            self._dependency_graph.clear()

            experiments = self.template_engine.list_available_experiments()

            for exp in experiments:
                exp_id = exp.get("id")

                if exp_id is None:
                    continue

                # 分类索引
                category = exp.get("category", "uncategorized")
                self._category_index[category].append(exp_id)

                # 依赖图
                try:
                    template = self.load_experiment(exp_id)
                    if template.prerequisites:
                        self._dependency_graph[exp_id] = template.prerequisites
                except Exception:
                    pass

    def _update_indices(self, template: ExperimentTemplate) -> None:
        """更新索引"""
        with self._index_lock, self._graph_lock:
            # 更新分类索引
            category = template.category if template.category else "uncategorized"
            if template.id not in self._category_index[category]:
                self._category_index[category].append(template.id)

            # 更新依赖图
            if template.prerequisites:
                self._dependency_graph[template.id] = template.prerequisites

    def _get_dependent_experiments(self, experiment_id: str) -> list[str]:
        """获取依赖于指定实验的实验列表"""
        dependents = []

        with self._graph_lock:
            for exp_id, prereqs in self._dependency_graph.items():
                if experiment_id in prereqs:
                    dependents.append(exp_id)

        return dependents
