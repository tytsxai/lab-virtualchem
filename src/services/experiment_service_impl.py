"""
实验服务实现
"""

import uuid
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


class ExperimentServiceImpl(ExperimentService):
    """实验服务具体实现"""

    def __init__(
        self,
        engine: IExperimentEngine,
        storage: IStorage,
        config: ExperimentServiceConfig | None = None,
    ):
        self.engine = engine
        self.storage = storage
        self.config = config or ExperimentServiceConfig()
        self._active_experiments: dict[str, Any] = {}

    def create_experiment(self, request: ExperimentRequest) -> ExperimentResponse:
        """创建实验"""
        try:
            # 加载模板
            template = self.storage.load(f"templates/{request.template_id}")
            if not template:
                return ExperimentResponse(success=False, experiment_id="", message=f"模板不存在: {request.template_id}")

            # 生成实验ID
            experiment_id = str(uuid.uuid4())

            # 初始化实验引擎
            self.engine.initialize(template, request.user_id)

            # 保存实验状态
            self._active_experiments[experiment_id] = {
                "id": experiment_id,
                "user_id": request.user_id,
                "template_id": request.template_id,
                "status": ExperimentStatus.NOT_STARTED,
                "created_at": datetime.now(),
            }

            return ExperimentResponse(
                success=True,
                experiment_id=experiment_id,
                status=ExperimentStatus.NOT_STARTED,
                message="实验创建成功",
            )

        except Exception as e:
            return ExperimentResponse(success=False, experiment_id="", message=f"创建实验失败: {str(e)}")

    def start_experiment(self, experiment_id: str) -> ExperimentResponse:
        """开始实验"""
        if experiment_id not in self._active_experiments:
            return ExperimentResponse(success=False, experiment_id=experiment_id, message="实验不存在")

        try:
            self.engine.start()
            self._active_experiments[experiment_id]["status"] = ExperimentStatus.IN_PROGRESS
            self._active_experiments[experiment_id]["started_at"] = datetime.now()

            return ExperimentResponse(
                success=True,
                experiment_id=experiment_id,
                status=ExperimentStatus.IN_PROGRESS,
                message="实验已开始",
            )

        except Exception as e:
            return ExperimentResponse(success=False, experiment_id=experiment_id, message=f"启动实验失败: {str(e)}")

    def submit_step(self, request: StepSubmissionRequest) -> StepSubmissionResponse:
        """提交步骤"""
        try:
            # 提交步骤到引擎
            passed, message, mistake = self.engine.submit_step(request.user_input)

            # 如果通过，进入下一步
            next_step_id = None
            if passed and self.engine.next_step():
                current_step = self.engine.get_current_step()
                next_step_id = current_step.id if current_step else None

            return StepSubmissionResponse(
                success=True,
                passed=passed,
                message=message,
                mistake=mistake,
                next_step_id=next_step_id,
            )

        except Exception as e:
            return StepSubmissionResponse(success=False, passed=False, message=f"提交失败: {str(e)}")

    def get_current_step(self, experiment_id: str) -> dict[str, Any] | None:
        """获取当前步骤"""
        if experiment_id not in self._active_experiments:
            return None

        step = self.engine.get_current_step()
        if not step:
            return None

        return {
            "id": step.id,
            "content": step.content,
            "type": step.type.value if hasattr(step.type, "value") else step.type,
            "options": step.options or {},
        }

    def get_progress(self, experiment_id: str) -> ProgressInfo | None:
        """获取实验进度"""
        if experiment_id not in self._active_experiments:
            return None

        exp = self._active_experiments[experiment_id]
        progress = self.engine.get_progress()

        return ProgressInfo(
            experiment_id=experiment_id,
            experiment_title=exp.get("template_id", ""),
            current_step=progress.get("current_step_index", 0),
            total_steps=progress.get("total_steps", 0),
            completion_rate=progress.get("completion_rate", 0.0),
            total_mistakes=progress.get("total_mistakes", 0),
            status=exp.get("status", ExperimentStatus.NOT_STARTED),
        )

    def complete_experiment(self, experiment_id: str) -> ExperimentResponse:
        """完成实验"""
        if experiment_id not in self._active_experiments:
            return ExperimentResponse(success=False, experiment_id=experiment_id, message="实验不存在")

        try:
            record = self.engine.complete()
            self._active_experiments[experiment_id]["status"] = ExperimentStatus.COMPLETED
            self._active_experiments[experiment_id]["completed_at"] = datetime.now()

            # 保存记录
            self.storage.save(f"records/{record.user_id}/{experiment_id}", record)

            return ExperimentResponse(
                success=True,
                experiment_id=experiment_id,
                record_id=record.id,
                status=ExperimentStatus.COMPLETED,
                message="实验已完成",
            )

        except Exception as e:
            return ExperimentResponse(success=False, experiment_id=experiment_id, message=f"完成实验失败: {str(e)}")

    def pause_experiment(self, experiment_id: str) -> ExperimentResponse:
        """暂停实验"""
        if experiment_id not in self._active_experiments:
            return ExperimentResponse(success=False, experiment_id=experiment_id, message="实验不存在")

        self._active_experiments[experiment_id]["status"] = ExperimentStatus.PAUSED
        return ExperimentResponse(
            success=True,
            experiment_id=experiment_id,
            status=ExperimentStatus.PAUSED,
            message="实验已暂停",
        )

    def resume_experiment(self, experiment_id: str) -> ExperimentResponse:
        """恢复实验"""
        if experiment_id not in self._active_experiments:
            return ExperimentResponse(success=False, experiment_id=experiment_id, message="实验不存在")

        self._active_experiments[experiment_id]["status"] = ExperimentStatus.IN_PROGRESS
        return ExperimentResponse(
            success=True,
            experiment_id=experiment_id,
            status=ExperimentStatus.IN_PROGRESS,
            message="实验已恢复",
        )

    def get_record(self, experiment_id: str) -> UserRecord | None:
        """获取实验记录"""
        if experiment_id not in self._active_experiments:
            return None

        return self.engine.get_record()

    def validate_experiment(self, template: ExperimentTemplate) -> tuple[bool, list[str]]:
        """验证实验模板"""
        errors = []

        if not template.id:
            errors.append("模板ID不能为空")

        if not template.title:
            errors.append("模板标题不能为空")

        if not template.steps:
            errors.append("模板必须包含至少一个步骤")

        return len(errors) == 0, errors
