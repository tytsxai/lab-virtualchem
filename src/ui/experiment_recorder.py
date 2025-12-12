"""
实验录制与回放系统
记录用户的所有操作并支持回放演示
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..utils.logger import get_logger

logger = get_logger(__name__)


class RecorderState(Enum):
    """录制器状态"""

    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    PLAYING = "playing"
    STOPPED = "stopped"


@dataclass
class RecordedAction:
    """录制的操作"""

    timestamp: float
    action_type: str
    target_id: str
    data: dict[str, Any]
    user_input: Any = None
    screenshot: str | None = None  # 截图路径


@dataclass
class ExperimentRecording:
    """实验录制数据"""

    id: str
    experiment_id: str
    user_id: str
    title: str
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    duration: float = 0.0
    actions: list[RecordedAction] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ExperimentRecorder(QObject):
    """实验录制器"""

    # 信号
    recording_started = Signal()
    recording_paused = Signal()
    recording_resumed = Signal()
    recording_stopped = Signal(float)  # 总时长
    action_recorded = Signal(str)  # 操作类型

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        self.state = RecorderState.IDLE
        self.recording: ExperimentRecording | None = None

        self.start_time = 0.0
        self.pause_time = 0.0
        self.total_pause_duration = 0.0

        # 是否自动保存截图
        self.auto_screenshot = False

        # 录制选项
        self.record_mouse_movement = False
        self.record_screenshots = False
        self.screenshot_interval = 2.0  # 秒

        logger.info("实验录制器初始化完成")

    def start_recording(self, experiment_id: str, user_id: str, title: str, description: str = "") -> None:
        """开始录制"""
        if self.state == RecorderState.RECORDING:
            logger.warning("录制已在进行中")
            return

        import uuid

        self.recording = ExperimentRecording(
            id=str(uuid.uuid4()), experiment_id=experiment_id, user_id=user_id, title=title, description=description
        )

        self.start_time = time.time()
        self.total_pause_duration = 0.0
        self.state = RecorderState.RECORDING

        self.recording_started.emit()

        logger.info(f"开始录制实验: {title}")

    def pause_recording(self) -> None:
        """暂停录制"""
        if self.state != RecorderState.RECORDING:
            return

        self.pause_time = time.time()
        self.state = RecorderState.PAUSED

        self.recording_paused.emit()

        logger.debug("录制已暂停")

    def resume_recording(self) -> None:
        """恢复录制"""
        if self.state != RecorderState.PAUSED:
            return

        pause_duration = time.time() - self.pause_time
        self.total_pause_duration += pause_duration
        self.state = RecorderState.RECORDING

        self.recording_resumed.emit()

        logger.debug("录制已恢复")

    def stop_recording(self) -> ExperimentRecording | None:
        """停止录制"""
        if self.state not in [RecorderState.RECORDING, RecorderState.PAUSED]:
            return None

        if not self.recording:
            return None

        # 计算总时长
        end_time = time.time()
        total_duration = end_time - self.start_time - self.total_pause_duration
        self.recording.duration = total_duration

        self.state = RecorderState.STOPPED

        self.recording_stopped.emit(total_duration)

        logger.info(f"录制完成，时长: {total_duration:.2f}秒")

        result = self.recording
        self.recording = None

        return result

    def record_action(
        self, action_type: str, target_id: str, data: dict[str, Any] | None = None, user_input: Any = None
    ) -> None:
        """记录操作"""
        if self.state != RecorderState.RECORDING or not self.recording:
            return

        current_time = time.time()
        relative_time = current_time - self.start_time - self.total_pause_duration

        action = RecordedAction(
            timestamp=relative_time,
            action_type=action_type,
            target_id=target_id,
            data=data or {},
            user_input=user_input,
        )

        # 可选：保存截图
        if self.auto_screenshot and self.record_screenshots:
            action.screenshot = self._capture_screenshot()

        self.recording.actions.append(action)

        self.action_recorded.emit(action_type)

        logger.debug(f"记录操作: {action_type} @ {relative_time:.2f}s")

    def _capture_screenshot(self) -> str | None:
        """捕获屏幕截图"""
        # 这里可以实现截图逻辑
        # 返回截图文件路径
        return None

    def get_current_recording(self) -> ExperimentRecording | None:
        """获取当前录制"""
        return self.recording

    def is_recording(self) -> bool:
        """是否正在录制"""
        return self.state == RecorderState.RECORDING


class ExperimentPlayer(QObject):
    """实验回放器"""

    # 信号
    playback_started = Signal()
    playback_paused = Signal()
    playback_resumed = Signal()
    playback_stopped = Signal()
    playback_completed = Signal()
    action_executed = Signal(RecordedAction)
    progress_updated = Signal(float)  # 0.0-1.0

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        self.state = RecorderState.IDLE
        self.recording: ExperimentRecording | None = None

        self.current_action_index = 0
        self.playback_speed = 1.0
        self.start_time = 0.0

        # 播放定时器
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._on_playback_tick)

        # 动作处理器
        self.action_handlers: dict[str, Callable[[RecordedAction], None]] = {}

        logger.info("实验回放器初始化完成")

    def load_recording(self, recording: ExperimentRecording) -> None:
        """加载录制数据"""
        self.recording = recording
        self.current_action_index = 0

        logger.info(f"加载录制: {recording.title}, 时长: {recording.duration:.2f}s")

    def start_playback(self, speed: float = 1.0) -> None:
        """开始回放"""
        if not self.recording or self.state == RecorderState.PLAYING:
            return

        self.playback_speed = speed
        self.current_action_index = 0
        self.start_time = time.time()
        self.state = RecorderState.PLAYING

        # 启动定时器，每100ms检查一次
        self.playback_timer.start(100)

        self.playback_started.emit()

        logger.info(f"开始回放，速度: {speed}x")

    def pause_playback(self) -> None:
        """暂停回放"""
        if self.state != RecorderState.PLAYING:
            return

        self.playback_timer.stop()
        self.state = RecorderState.PAUSED

        self.playback_paused.emit()

        logger.debug("回放已暂停")

    def resume_playback(self) -> None:
        """恢复回放"""
        if self.state != RecorderState.PAUSED or not self.recording:
            return

        # 调整开始时间以补偿暂停时间
        elapsed = self._get_elapsed_time()
        self.start_time = time.time() - elapsed

        self.state = RecorderState.PLAYING
        self.playback_timer.start(100)

        self.playback_resumed.emit()

        logger.debug("回放已恢复")

    def stop_playback(self) -> None:
        """停止回放"""
        if self.state not in [RecorderState.PLAYING, RecorderState.PAUSED]:
            return

        self.playback_timer.stop()
        self.state = RecorderState.STOPPED
        self.current_action_index = 0

        self.playback_stopped.emit()

        logger.info("回放已停止")

    def seek_to(self, progress: float) -> None:
        """跳转到指定位置 (0.0-1.0)"""
        if not self.recording:
            return

        target_time = self.recording.duration * progress

        # 找到对应的动作索引
        self.current_action_index = 0
        for i, action in enumerate(self.recording.actions):
            if action.timestamp <= target_time:
                self.current_action_index = i
            else:
                break

        # 如果正在播放，调整开始时间
        if self.state == RecorderState.PLAYING:
            self.start_time = time.time() - target_time / self.playback_speed

        self.progress_updated.emit(progress)

        logger.debug(f"跳转到 {progress:.1%}")

    def set_playback_speed(self, speed: float) -> None:
        """设置回放速度"""
        if speed <= 0:
            return

        # 如果正在播放，调整开始时间以保持连续性
        if self.state == RecorderState.PLAYING:
            elapsed = self._get_elapsed_time()
            self.playback_speed = speed
            self.start_time = time.time() - elapsed
        else:
            self.playback_speed = speed

        logger.info(f"回放速度设置为: {speed}x")

    def register_action_handler(self, action_type: str, handler: Callable[[RecordedAction], None]) -> None:
        """注册动作处理器"""
        self.action_handlers[action_type] = handler
        logger.debug(f"注册动作处理器: {action_type}")

    def _on_playback_tick(self) -> None:
        """回放定时器触发"""
        if not self.recording or self.state != RecorderState.PLAYING:
            return

        elapsed_time = self._get_elapsed_time()

        # 执行所有应该执行的动作
        while self.current_action_index < len(self.recording.actions):
            action = self.recording.actions[self.current_action_index]

            if action.timestamp <= elapsed_time:
                self._execute_action(action)
                self.current_action_index += 1
            else:
                break

        # 更新进度
        if self.recording.duration > 0:
            progress = min(1.0, elapsed_time / self.recording.duration)
            self.progress_updated.emit(progress)

        # 检查是否完成
        if self.current_action_index >= len(self.recording.actions):
            self.playback_timer.stop()
            self.state = RecorderState.STOPPED
            self.playback_completed.emit()
            logger.info("回放完成")

    def _execute_action(self, action: RecordedAction) -> None:
        """执行动作"""
        # 调用对应的处理器
        if action.action_type in self.action_handlers:
            try:
                self.action_handlers[action.action_type](action)
            except Exception as e:
                logger.error(f"执行动作失败: {action.action_type} - {e}", exc_info=True)

        # 发送信号
        self.action_executed.emit(action)

        logger.debug(f"执行动作: {action.action_type} @ {action.timestamp:.2f}s")

    def _get_elapsed_time(self) -> float:
        """获取已播放时间"""
        return (time.time() - self.start_time) * self.playback_speed


class RecorderControlWidget(QWidget):
    """录制控制界面"""

    def __init__(self, recorder: ExperimentRecorder, parent: QWidget | None = None):
        super().__init__(parent)

        self.recorder = recorder

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """设置UI"""
        layout = QVBoxLayout(self)

        # 状态显示
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # 时间显示
        self.time_label = QLabel("00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("font-size: 18pt; font-weight: bold;")
        layout.addWidget(self.time_label)

        # 控制按钮
        btn_layout = QHBoxLayout()

        self.record_btn = QPushButton("开始录制")
        self.record_btn.clicked.connect(self._on_record_clicked)
        btn_layout.addWidget(self.record_btn)

        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        btn_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        btn_layout.addWidget(self.stop_btn)

        layout.addLayout(btn_layout)

        # 时间更新定时器
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self._update_time_display)

    def _connect_signals(self) -> None:
        """连接信号"""
        self.recorder.recording_started.connect(self._on_recording_started)
        self.recorder.recording_paused.connect(self._on_recording_paused)
        self.recorder.recording_resumed.connect(self._on_recording_resumed)
        self.recorder.recording_stopped.connect(self._on_recording_stopped)

    def _on_record_clicked(self) -> None:
        """录制按钮点击"""
        # 这里应该弹出对话框输入录制信息
        # 简化实现，直接开始
        self.recorder.start_recording(experiment_id="EXP-001", user_id="user_001", title="实验录制")

    def _on_pause_clicked(self) -> None:
        """暂停按钮点击"""
        if self.recorder.state == RecorderState.RECORDING:
            self.recorder.pause_recording()
        elif self.recorder.state == RecorderState.PAUSED:
            self.recorder.resume_recording()

    def _on_stop_clicked(self) -> None:
        """停止按钮点击"""
        self.recorder.stop_recording()

    def _on_recording_started(self) -> None:
        """录制开始"""
        self.status_label.setText("⏺ 录制中")
        self.record_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.time_timer.start(100)

    def _on_recording_paused(self) -> None:
        """录制暂停"""
        self.status_label.setText("⏸ 已暂停")
        self.pause_btn.setText("继续")

    def _on_recording_resumed(self) -> None:
        """录制恢复"""
        self.status_label.setText("⏺ 录制中")
        self.pause_btn.setText("暂停")

    def _on_recording_stopped(self, _duration: float) -> None:
        """录制停止"""
        self.status_label.setText("✓ 已完成")
        self.record_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.time_timer.stop()

    def _update_time_display(self) -> None:
        """更新时间显示"""
        if self.recorder.state in [RecorderState.RECORDING, RecorderState.PAUSED]:
            elapsed = time.time() - self.recorder.start_time - self.recorder.total_pause_duration
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.time_label.setText(f"{minutes:02d}:{seconds:02d}")


class PlayerControlWidget(QWidget):
    """回放控制界面"""

    def __init__(self, player: ExperimentPlayer, parent: QWidget | None = None):
        super().__init__(parent)

        self.player = player

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """设置UI"""
        layout = QVBoxLayout(self)

        # 进度条
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        layout.addWidget(self.progress_slider)

        # 时间显示
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("00:00")
        self.total_time_label = QLabel("00:00")
        time_layout.addWidget(self.current_time_label)
        time_layout.addStretch()
        time_layout.addWidget(self.total_time_label)
        layout.addLayout(time_layout)

        # 控制按钮
        btn_layout = QHBoxLayout()

        self.play_btn = QPushButton("▶ 播放")
        self.play_btn.clicked.connect(self._on_play_clicked)
        btn_layout.addWidget(self.play_btn)

        self.speed_label = QLabel("1.0x")
        btn_layout.addWidget(self.speed_label)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(25, 200)  # 0.25x - 2.0x
        self.speed_slider.setValue(100)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        btn_layout.addWidget(self.speed_slider)

        layout.addLayout(btn_layout)

    def _connect_signals(self) -> None:
        """连接信号"""
        self.player.playback_started.connect(self._on_playback_started)
        self.player.playback_paused.connect(self._on_playback_paused)
        self.player.playback_stopped.connect(self._on_playback_stopped)
        self.player.progress_updated.connect(self._on_progress_updated)

    def _on_play_clicked(self) -> None:
        """播放按钮点击"""
        if self.player.state == RecorderState.PLAYING:
            self.player.pause_playback()
        elif self.player.state in [RecorderState.IDLE, RecorderState.PAUSED, RecorderState.STOPPED]:
            self.player.start_playback()

    def _on_speed_changed(self, value: int) -> None:
        """速度改变"""
        speed = value / 100.0
        self.player.set_playback_speed(speed)
        self.speed_label.setText(f"{speed:.1f}x")

    def _on_slider_pressed(self) -> None:
        """进度条按下"""
        if self.player.state == RecorderState.PLAYING:
            self.player.pause_playback()

    def _on_slider_released(self) -> None:
        """进度条释放"""
        progress = self.progress_slider.value() / 1000.0
        self.player.seek_to(progress)
        if self.player.state == RecorderState.PAUSED:
            self.player.resume_playback()

    def _on_playback_started(self) -> None:
        """回放开始"""
        self.play_btn.setText("⏸ 暂停")

    def _on_playback_paused(self) -> None:
        """回放暂停"""
        self.play_btn.setText("▶ 播放")

    def _on_playback_stopped(self) -> None:
        """回放停止"""
        self.play_btn.setText("▶ 播放")

    def _on_progress_updated(self, progress: float) -> None:
        """进度更新"""
        self.progress_slider.setValue(int(progress * 1000))

        if self.player.recording:
            current_time = progress * self.player.recording.duration
            total_time = self.player.recording.duration

            current_min = int(current_time // 60)
            current_sec = int(current_time % 60)
            total_min = int(total_time // 60)
            total_sec = int(total_time % 60)

            self.current_time_label.setText(f"{current_min:02d}:{current_sec:02d}")
            self.total_time_label.setText(f"{total_min:02d}:{total_sec:02d}")


def save_recording(recording: ExperimentRecording, filepath: str) -> None:
    """保存录制数据"""
    data = {
        "id": recording.id,
        "experiment_id": recording.experiment_id,
        "user_id": recording.user_id,
        "title": recording.title,
        "description": recording.description,
        "created_at": recording.created_at.isoformat(),
        "duration": recording.duration,
        "actions": [
            {
                "timestamp": action.timestamp,
                "action_type": action.action_type,
                "target_id": action.target_id,
                "data": action.data,
                "user_input": action.user_input,
                "screenshot": action.screenshot,
            }
            for action in recording.actions
        ],
        "metadata": recording.metadata,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"录制数据已保存到: {filepath}")


def load_recording(filepath: str) -> ExperimentRecording:
    """加载录制数据"""
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    recording = ExperimentRecording(
        id=data["id"],
        experiment_id=data["experiment_id"],
        user_id=data["user_id"],
        title=data["title"],
        description=data.get("description", ""),
        created_at=datetime.fromisoformat(data["created_at"]),
        duration=data["duration"],
        metadata=data.get("metadata", {}),
    )

    for action_data in data["actions"]:
        action = RecordedAction(
            timestamp=action_data["timestamp"],
            action_type=action_data["action_type"],
            target_id=action_data["target_id"],
            data=action_data["data"],
            user_input=action_data.get("user_input"),
            screenshot=action_data.get("screenshot"),
        )
        recording.actions.append(action)

    logger.info(f"录制数据已从 {filepath} 加载")

    return recording
