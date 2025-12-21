"""
实验服务实现
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any

from src.contracts.experiment_service import (
    ExperimentRequest,
    ExperimentResponse,
    ExperimentService,
    ExperimentServiceConfig,
    ExperimentStatus,
    ProgressInfo,
    StepSubmissionRequest,
    StepSubmissionResponse,
)
from src.interfaces.experiment import IExperimentEngine
from src.interfaces.storage import IStorage
from src.models.experiment import ExperimentTemplate
from src.models.user_record import UserRecord

logger = logging.getLogger(__name__)


class ExperimentServiceImpl(ExperimentService):
    """实验服务具体实现"""

    def __init__(
        self,
        engine_factory: Callable[[], IExperimentEngine] | None = None,
        storage: IStorage[Any] | None = None,
        config: ExperimentServiceConfig | None = None,
        *,
        template_engine: Any | None = None,
        record_store: Any | None = None,
        engine: IExperimentEngine | None = None,
    ):
        if engine_factory is None and engine is None:
            raise ValueError("必须提供 engine_factory 或 engine 实例")
        if storage is None:
            raise ValueError("storage 不能为空")

        self.engine_factory = engine_factory
        self.storage = storage
        self.config = config or ExperimentServiceConfig()
        self.template_engine = template_engine
        self.record_store = record_store
        self._default_engine = engine
        self._active_experiments: dict[str, dict[str, Any]] = {}
        self._closed = False

    def __enter__(self) -> "ExperimentServiceImpl":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.close()

    def close(self) -> None:
        """释放运行中实验相关资源。"""
        if self._closed:
            return
        for ctx in list(self._active_experiments.values()):
            engine = ctx.get("engine")
            if engine is None:
                continue
            for method_name in ("stop", "shutdown", "close"):
                method = getattr(engine, method_name, None)
                if callable(method):
                    try:
                        method()
                    except Exception:  # noqa: BLE001
                        logger.debug("engine.%s() 执行失败", method_name)
                    break
        self._active_experiments.clear()
        self._closed = True

    # ------------------------------------------------------------------
    # 生命周期管理
    # ------------------------------------------------------------------
    def create_experiment(self, request: ExperimentRequest) -> ExperimentResponse:
        try:
            template = self._load_template(request.template_id)
            if template is None:
                return ExperimentResponse(
                    success=False,
                    experiment_id="",
                    message=f"模板不存在: {request.template_id}",
                )

            experiment_id = str(uuid.uuid4())
            engine = self._create_engine()
            engine.initialize(template, request.user_id)

            self._active_experiments[experiment_id] = {
                "id": experiment_id,
                "user_id": request.user_id,
                "template_id": template.id,
                "status": ExperimentStatus.NOT_STARTED,
                "created_at": datetime.now(),
                "engine": engine,
            }

            return ExperimentResponse(
                success=True,
                experiment_id=experiment_id,
                status=ExperimentStatus.NOT_STARTED,
                message="实验创建成功",
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("创建实验失败: %s", exc)
            return ExperimentResponse(
                success=False, experiment_id="", message=f"创建实验失败: {exc}"
            )

    def start_experiment(self, experiment_id: str) -> ExperimentResponse:
        ctx = self._active_experiments.get(experiment_id)
        if not ctx:
            return ExperimentResponse(
                success=False, experiment_id=experiment_id, message="实验不存在"
            )

        try:
            engine = ctx["engine"]
            engine.start()
            ctx["status"] = ExperimentStatus.IN_PROGRESS
            ctx["started_at"] = datetime.now()
            return ExperimentResponse(
                success=True,
                experiment_id=experiment_id,
                status=ExperimentStatus.IN_PROGRESS,
                message="实验已开始",
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("启动实验失败: %s", exc)
            return ExperimentResponse(
                success=False,
                experiment_id=experiment_id,
                message=f"启动实验失败: {exc}",
            )

    def submit_step(self, request: StepSubmissionRequest) -> StepSubmissionResponse:
        ctx = self._active_experiments.get(request.experiment_id)
        if not ctx:
            return StepSubmissionResponse(
                success=False, passed=False, message="实验不存在"
            )

        engine: IExperimentEngine = ctx["engine"]

        try:
            passed, message, mistake = engine.submit_step(request.user_input)
            next_step_id = None
            if passed and engine.next_step():
                step = engine.get_current_step()
                next_step_id = step.id if step else None

            return StepSubmissionResponse(
                success=True,
                passed=passed,
                message=message,
                mistake=mistake,
                next_step_id=next_step_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("步骤提交失败: %s", exc)
            return StepSubmissionResponse(
                success=False, passed=False, message=f"提交失败: {exc}"
            )

    def get_current_step(self, experiment_id: str) -> dict[str, Any] | None:
        ctx = self._active_experiments.get(experiment_id)
        if not ctx:
            return None

        engine: IExperimentEngine = ctx["engine"]
        step = engine.get_current_step()
        if not step:
            return None

        return {
            "id": getattr(step, "id", None),
            "content": getattr(step, "content", None),
            "type": step.type.value
            if hasattr(step.type, "value")
            else getattr(step, "type", None),
            "options": getattr(step, "options", {}) or {},
        }

    def get_progress(self, experiment_id: str) -> ProgressInfo | None:
        ctx = self._active_experiments.get(experiment_id)
        if not ctx:
            return None

        engine: IExperimentEngine = ctx["engine"]
        progress = engine.get_progress() or {}

        return ProgressInfo(
            experiment_id=experiment_id,
            experiment_title=ctx.get("template_id", ""),
            current_step=progress.get("current_step_index", 0),
            total_steps=progress.get("total_steps", 0),
            completion_rate=progress.get("completion_rate", 0.0),
            total_mistakes=progress.get("total_mistakes", 0),
            status=ctx.get("status", ExperimentStatus.NOT_STARTED),
            elapsed_time=progress.get("elapsed_time"),
        )

    def complete_experiment(self, experiment_id: str) -> ExperimentResponse:
        ctx = self._active_experiments.get(experiment_id)
        if not ctx:
            return ExperimentResponse(
                success=False, experiment_id=experiment_id, message="实验不存在"
            )

        engine: IExperimentEngine = ctx["engine"]
        try:
            record = engine.complete()
            ctx["status"] = ExperimentStatus.COMPLETED
            ctx["completed_at"] = datetime.now()
            self._persist_record(record, experiment_id)

            return ExperimentResponse(
                success=True,
                experiment_id=experiment_id,
                record_id=getattr(record, "id", None),
                status=ExperimentStatus.COMPLETED,
                message="实验已完成",
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("完成实验失败: %s", exc)
            return ExperimentResponse(
                success=False,
                experiment_id=experiment_id,
                message=f"完成实验失败: {exc}",
            )

    def pause_experiment(self, experiment_id: str) -> ExperimentResponse:
        ctx = self._active_experiments.get(experiment_id)
        if not ctx:
            return ExperimentResponse(
                success=False, experiment_id=experiment_id, message="实验不存在"
            )

        ctx["status"] = ExperimentStatus.PAUSED
        return ExperimentResponse(
            success=True,
            experiment_id=experiment_id,
            status=ExperimentStatus.PAUSED,
            message="实验已暂停",
        )

    def resume_experiment(self, experiment_id: str) -> ExperimentResponse:
        ctx = self._active_experiments.get(experiment_id)
        if not ctx:
            return ExperimentResponse(
                success=False, experiment_id=experiment_id, message="实验不存在"
            )

        ctx["status"] = ExperimentStatus.IN_PROGRESS
        return ExperimentResponse(
            success=True,
            experiment_id=experiment_id,
            status=ExperimentStatus.IN_PROGRESS,
            message="实验已恢复",
        )

    def get_record(self, experiment_id: str) -> UserRecord | None:
        ctx = self._active_experiments.get(experiment_id)
        if not ctx:
            return None

        engine: IExperimentEngine = ctx["engine"]
        return engine.get_record()

    def validate_experiment(
        self, template: ExperimentTemplate
    ) -> tuple[bool, list[str]]:
        errors = []
        if not template.id:
            errors.append("模板ID不能为空")
        if not template.title:
            errors.append("模板标题不能为空")
        if not template.steps:
            errors.append("模板必须包含至少一个步骤")
        return len(errors) == 0, errors

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------
    def _create_engine(self) -> IExperimentEngine:
        if self.engine_factory:
            return self.engine_factory()
        if self._default_engine:
            return self._default_engine
        raise RuntimeError("无法创建实验引擎")

    def _load_template(self, template_id: str) -> ExperimentTemplate | None:
        key = f"templates/{template_id}"
        template = self.storage.load(key)
        if template is None and self.template_engine:
            try:
                template_path = (
                    self.template_engine.templates_dir / f"{template_id}.yaml"
                )
                template = self.template_engine.load_experiment(template_path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("模板引擎加载失败: %s", exc)
                template = None

        if template is None:
            return None

        if isinstance(template, ExperimentTemplate):
            return template

        if isinstance(template, dict):
            try:
                return ExperimentTemplate(**template)
            except Exception as exc:  # noqa: BLE001
                logger.error("模板数据无效: %s", exc)
                return None

        return None

    def _persist_record(self, record: UserRecord, experiment_id: str) -> None:
        if record is None:
            return

        try:
            if self.record_store and hasattr(self.record_store, "save_record"):
                self.record_store.save_record(record)
            else:
                key = f"records/{record.user_id}/{experiment_id}"
                self.storage.save(key, record)
        except Exception as exc:  # noqa: BLE001
            logger.warning("保存实验记录失败: %s", exc)
