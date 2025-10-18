"""语音交互模块

离线语音识别和语音合成，支持中英双语
"""

from .voice_controller import (
    TTS_AVAILABLE,
    VOSK_AVAILABLE,
    VoiceController,
    create_experiment_controller,
)

__all__ = ["VoiceController", "create_experiment_controller", "VOSK_AVAILABLE", "TTS_AVAILABLE"]
