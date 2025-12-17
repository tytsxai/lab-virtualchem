import asyncio
import contextlib
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any

"""CQRS (命令查询职责分离) 架构"""

logger = logging.getLogger(__name__)


class CommandStatus(Enum):
    """命令状态"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QueryStatus(Enum):
    """查询状态"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Command:
    """命令基类"""

    command_id: str = field(default_factory=lambda: f"cmd_{int(time.time() * 1000)}")
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "command_id": self.command_id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "data": self.data,
            "metadata": self.metadata,
        }


@dataclass
class Query:
    """查询基类"""

    query_id: str = field(default_factory=lambda: f"qry_{int(time.time() * 1000)}")
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "query_id": self.query_id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "data": self.data,
            "metadata": self.metadata,
        }


@dataclass
class CommandResult:
    """命令结果"""

    command_id: str
    status: CommandStatus
    result: Any = None
    error: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "command_id": self.command_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class QueryResult:
    """查询结果"""

    query_id: str
    status: QueryStatus
    result: Any = None
    error: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "query_id": self.query_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


class ICommandHandler(ABC):
    """命令处理器接口"""

    @abstractmethod
    def handle(self, _command: Command) -> CommandResult:
        """处理命令"""
        pass


class IQueryHandler(ABC):
    """查询处理器接口"""

    @abstractmethod
    def handle(self, _query: Query) -> QueryResult:
        """处理查询"""
        pass


class CommandBus:
    """命令总线"""

    def __init__(self, max_queue_size: int = 1000):
        """初始化命令总线

        Args:
            max_queue_size: 最大队列大小
        """
        self.max_queue_size = max_queue_size
        self.handlers: dict[str, ICommandHandler] = {}
        self.command_queue: asyncio.Queue[Command] = asyncio.Queue(
            maxsize=max_queue_size
        )
        self.running = False
        self.worker_task: asyncio.Task[None] | None = None

        # 统计信息
        self.stats = {
            "commands_received": 0,
            "commands_processed": 0,
            "commands_failed": 0,
            "queue_size": 0,
        }

        # 命令结果缓存
        self.results: dict[str, CommandResult] = {}

        logger.info("命令总线已初始化")

    def register_handler(self, command_type: str, handler: ICommandHandler) -> None:
        """注册命令处理器

        Args:
            command_type: 命令类型
            handler: 命令处理器
        """
        self.handlers[command_type] = handler
        logger.info(f"注册命令处理器: {command_type}")

    def unregister_handler(self, command_type: str) -> bool:
        """注销命令处理器

        Args:
            command_type: 命令类型

        Returns:
            是否成功注销
        """
        if command_type in self.handlers:
            del self.handlers[command_type]
            logger.info(f"注销命令处理器: {command_type}")
            return True
        return False

    async def send(self, command: Command, command_type: str) -> CommandResult:
        """发送命令

        Args:
            command: 命令
            command_type: 命令类型

        Returns:
            命令结果
        """
        if command_type not in self.handlers:
            return CommandResult(
                command_id=command.command_id,
                status=CommandStatus.FAILED,
                error=f"未找到命令处理器: {command_type}",
            )

        try:
            # 将命令放入队列
            await self.command_queue.put((command, command_type))
            self.stats["commands_received"] += 1
            self.stats["queue_size"] = self.command_queue.qsize()

            logger.debug(f"命令已发送: {command_type} ({command.command_id})")

            # 等待处理结果
            result = await self._wait_for_result(command.command_id)
            return result

        except Exception as e:
            logger.error(f"发送命令失败: {e}")
            return CommandResult(
                command_id=command.command_id, status=CommandStatus.FAILED, error=str(e)
            )

    def send_sync(self, command: Command, command_type: str) -> CommandResult:
        """同步发送命令

        Args:
            command: 命令
            command_type: 命令类型

        Returns:
            命令结果
        """
        if command_type not in self.handlers:
            return CommandResult(
                command_id=command.command_id,
                status=CommandStatus.FAILED,
                error=f"未找到命令处理器: {command_type}",
            )

        try:
            handler = self.handlers[command_type]
            result = handler.handle(command)

            self.stats["commands_processed"] += 1
            if result.status == CommandStatus.FAILED:
                self.stats["commands_failed"] += 1

            logger.debug(f"命令已处理: {command_type} ({command.command_id})")
            return result

        except Exception as e:
            logger.error(f"处理命令失败: {e}")
            self.stats["commands_failed"] += 1
            return CommandResult(
                command_id=command.command_id, status=CommandStatus.FAILED, error=str(e)
            )

    async def _worker_loop(self) -> None:
        """工作循环"""
        while self.running:
            try:
                # 从队列获取命令
                command, command_type = await asyncio.wait_for(
                    self.command_queue.get(), timeout=1.0
                )

                # 处理命令
                handler = self.handlers[command_type]
                result = handler.handle(command)

                # 存储结果
                self._store_result(command.command_id, result)

                # 标记任务完成
                self.command_queue.task_done()

                self.stats["commands_processed"] += 1
                if result.status == CommandStatus.FAILED:
                    self.stats["commands_failed"] += 1

                logger.debug(f"命令已处理: {command_type} ({command.command_id})")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"命令总线工作循环错误: {e}")

    def _store_result(self, command_id: str, result: CommandResult) -> None:
        """存储命令结果

        Args:
            command_id: 命令ID
            result: 命令结果
        """
        # 存储到内存缓存，设置过期时间
        self.results[command_id] = result

        # 只保留最近的结果，避免内存泄漏
        if len(self.results) > 1000:
            # 删除最旧的结果
            oldest_keys = list(self.results.keys())[:100]
            for key in oldest_keys:
                self.results.pop(key, None)

    def _wait_for_result(self, command_id: str, timeout: float = 30.0) -> CommandResult:
        """等待命令结果

        Args:
            command_id: 命令ID
            timeout: 超时时间（秒）

        Returns:
            命令结果
        """
        import time

        start_time = time.time()

        while time.time() - start_time < timeout:
            if command_id in self.results:
                return self.results.pop(command_id)

            # 短暂休眠避免CPU占用
            time.sleep(0.01)

        # 超时返回失败结果
        logger.warning(f"等待命令结果超时: {command_id}")
        return CommandResult(
            command_id=command_id, status=CommandStatus.FAILED, error="等待结果超时"
        )

    async def start(self) -> None:
        """启动命令总线"""
        if self.running:
            return

        self.running = True
        self.worker_task = asyncio.create_task(self._worker_loop())

        logger.info("命令总线已启动")

    async def stop(self) -> None:
        """停止命令总线"""
        if not self.running:
            return

        self.running = False

        if self.worker_task:
            self.worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.worker_task

        logger.info("命令总线已停止")

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息
        """
        return {
            "running": self.running,
            "queue_size": self.command_queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "handlers_count": len(self.handlers),
            **self.stats,
        }


class QueryBus:
    """查询总线"""

    def __init__(self) -> None:
        """初始化查询总线"""
        self.handlers: dict[str, IQueryHandler] = {}

        # 统计信息
        self.stats = {
            "queries_received": 0,
            "queries_processed": 0,
            "queries_failed": 0,
        }

        logger.info("查询总线已初始化")

    def register_handler(self, query_type: str, handler: IQueryHandler) -> None:
        """注册查询处理器

        Args:
            query_type: 查询类型
            handler: 查询处理器
        """
        self.handlers[query_type] = handler
        logger.info(f"注册查询处理器: {query_type}")

    def unregister_handler(self, query_type: str) -> bool:
        """注销查询处理器

        Args:
            query_type: 查询类型

        Returns:
            是否成功注销
        """
        if query_type in self.handlers:
            del self.handlers[query_type]
            logger.info(f"注销查询处理器: {query_type}")
            return True
        return False

    def _query(self, query: Query, query_type: str) -> QueryResult:
        """执行查询

        Args:
            query: 查询
            query_type: 查询类型

        Returns:
            查询结果
        """
        if query_type not in self.handlers:
            return QueryResult(
                query_id=query.query_id,
                status=QueryStatus.FAILED,
                error=f"未找到查询处理器: {query_type}",
            )

        try:
            handler = self.handlers[query_type]
            result = handler.handle(query)

            self.stats["queries_processed"] += 1
            if result.status == QueryStatus.FAILED:
                self.stats["queries_failed"] += 1

            logger.debug(f"查询已处理: {query_type} ({query.query_id})")
            return result

        except Exception as e:
            logger.error(f"处理查询失败: {e}")
            self.stats["queries_failed"] += 1
            return QueryResult(
                query_id=query.query_id, status=QueryStatus.FAILED, error=str(e)
            )

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息
        """
        return {"handlers_count": len(self.handlers), **self.stats}


class CQRSManager:
    """CQRS管理器"""

    def __init__(self) -> None:
        """初始化CQRS管理器"""
        self.command_bus = CommandBus()
        self.query_bus = QueryBus()

        logger.info("CQRS管理器已初始化")

    def register_command_handler(
        self, command_type: str, handler: ICommandHandler
    ) -> None:
        """注册命令处理器"""
        self.command_bus.register_handler(command_type, handler)

    def register_query_handler(self, query_type: str, handler: IQueryHandler) -> None:
        """注册查询处理器"""
        self.query_bus.register_handler(query_type, handler)

    async def send_command(self, command: Command, command_type: str) -> CommandResult:
        """发送命令"""
        return await self.command_bus.send(command, command_type)

    def send_command_sync(self, command: Command, command_type: str) -> CommandResult:
        """同步发送命令"""
        return self.command_bus.send_sync(command, command_type)

    def execute_query(self, query: Query, query_type: str) -> QueryResult:
        """执行查询"""
        return self.query_bus.query(query, query_type)

    async def start(self) -> None:
        """启动CQRS管理器"""
        await self.command_bus.start()
        logger.info("CQRS管理器已启动")

    async def stop(self) -> None:
        """停止CQRS管理器"""
        await self.command_bus.stop()
        logger.info("CQRS管理器已停止")

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "command_bus": self.command_bus.get_statistics(),
            "query_bus": self.query_bus.get_statistics(),
        }


# 具体实现示例


class CreateExperimentCommand(Command):
    """创建实验命令"""

    pass


class UpdateExperimentCommand(Command):
    """更新实验命令"""

    pass


class DeleteExperimentCommand(Command):
    """删除实验命令"""

    pass


class GetExperimentQuery(Query):
    """获取实验查询"""

    pass


class ListExperimentsQuery(Query):
    """列出实验查询"""

    pass


class ExperimentCommandHandler(ICommandHandler):
    """实验命令处理器"""

    def __init__(self, experiment_service: Any = None) -> None:
        self.experiment_service = experiment_service

    def handle(self, command: Command) -> CommandResult:
        """处理命令"""
        try:
            if isinstance(command, CreateExperimentCommand):
                result = self._handle_create_experiment(command)
            elif isinstance(command, UpdateExperimentCommand):
                result = self._handle_update_experiment(command)
            elif isinstance(command, DeleteExperimentCommand):
                result = self._handle_delete_experiment(command)
            else:
                return CommandResult(
                    command_id=command.command_id,
                    status=CommandStatus.FAILED,
                    error="未知命令类型",
                )

            return CommandResult(
                command_id=command.command_id,
                status=CommandStatus.COMPLETED,
                result=result,
            )

        except Exception as e:
            logger.error(f"处理实验命令失败: {e}")
            return CommandResult(
                command_id=command.command_id, status=CommandStatus.FAILED, error=str(e)
            )

    def _handle_create_experiment(self, _command: CreateExperimentCommand) -> Any:
        """处理创建实验命令"""
        # 实现创建实验逻辑
        return {"experiment_id": "exp_001", "status": "created"}

    def _handle_update_experiment(self, command: UpdateExperimentCommand) -> Any:
        """处理更新实验命令"""
        # 实现更新实验逻辑
        return {"experiment_id": command.data.get("id"), "status": "updated"}

    def _handle_delete_experiment(self, command: DeleteExperimentCommand) -> Any:
        """处理删除实验命令"""
        # 实现删除实验逻辑
        return {"experiment_id": command.data.get("id"), "status": "deleted"}


class ExperimentQueryHandler(IQueryHandler):
    """实验查询处理器"""

    def __init__(self, experiment_repository: Any = None) -> None:
        self.experiment_repository = experiment_repository

    def handle(self, query: Query) -> QueryResult:
        """处理查询"""
        try:
            if isinstance(query, GetExperimentQuery):
                result = self._handle_get_experiment(query)
            elif isinstance(query, ListExperimentsQuery):
                result = self._handle_list_experiments(query)
            else:
                return QueryResult(
                    query_id=query.query_id,
                    status=QueryStatus.FAILED,
                    error="未知查询类型",
                )

            return QueryResult(
                query_id=query.query_id, status=QueryStatus.COMPLETED, result=result
            )

        except Exception as e:
            logger.error(f"处理实验查询失败: {e}")
            return QueryResult(
                query_id=query.query_id, status=QueryStatus.FAILED, error=str(e)
            )

    def _handle_get_experiment(self, query: GetExperimentQuery) -> Any:
        """处理获取实验查询"""
        experiment_id = query.data.get("id")
        # 实现获取实验逻辑
        return {"id": experiment_id, "title": "测试实验"}

    def _handle_list_experiments(self, _query: ListExperimentsQuery) -> Any:
        """处理列出实验查询"""
        # 实现列出实验逻辑
        return [
            {"id": "exp_001", "title": "实验1"},
            {"id": "exp_002", "title": "实验2"},
        ]


# 全局CQRS管理器
cqrs_manager = CQRSManager()


def command_handler(
    command_type: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """命令处理器装饰器

    Args:
        command_type: 命令类型
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # 创建处理器
        class Handler(ICommandHandler):
            def handle(self, command: Command) -> CommandResult:
                try:
                    result = func(command)
                    return CommandResult(
                        command_id=command.command_id,
                        status=CommandStatus.COMPLETED,
                        result=result,
                    )
                except Exception as e:
                    return CommandResult(
                        command_id=command.command_id,
                        status=CommandStatus.FAILED,
                        error=str(e),
                    )

        # 注册处理器
        cqrs_manager.register_command_handler(command_type, Handler())
        return wrapper

    return decorator


def query_handler(
    query_type: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """查询处理器装饰器

    Args:
        query_type: 查询类型
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # 创建处理器
        class Handler(IQueryHandler):
            def handle(self, query: Query) -> QueryResult:
                try:
                    result = func(query)
                    return QueryResult(
                        query_id=query.query_id,
                        status=QueryStatus.COMPLETED,
                        result=result,
                    )
                except Exception as e:
                    return QueryResult(
                        query_id=query.query_id, status=QueryStatus.FAILED, error=str(e)
                    )

        # 注册处理器
        cqrs_manager.register_query_handler(query_type, Handler())
        return wrapper

    return decorator
