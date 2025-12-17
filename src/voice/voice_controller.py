"""语音交互控制模块

使用Vosk (离线语音识别) + pyttsx3 (文本转语音) 实现:
- 完全离线工作
- 语音指令控制实验
- 实验步骤语音播报
- 数据实时语音反馈
- 中英双语支持
"""

import json
import logging
import queue
import sys
import threading
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
    from vosk import KaldiRecognizer, Model

    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    logger.warning("Vosk未安装，语音识别功能不可用")

try:
    import pyttsx3

    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logger.warning("pyttsx3未安装，语音合成功能不可用")


class VoiceController:
    """语音控制器"""

    # 默认指令映射
    DEFAULT_COMMANDS = {
        # 实验控制
        "开始实验": "start_experiment",
        "停止实验": "stop_experiment",
        "暂停实验": "pause_experiment",
        "继续实验": "resume_experiment",
        # 试剂操作
        "添加试剂": "add_reagent",
        "添加盐酸": "add_hcl",
        "添加氢氧化钠": "add_naoh",
        # 数据记录
        "记录数据": "record_data",
        "查看数据": "view_data",
        "保存数据": "save_data",
        # 系统控制
        "打开主题设置": "open_theme",
        "切换深色模式": "toggle_dark",
        "切换浅色模式": "toggle_light",
        # 帮助
        "帮助": "show_help",
        "显示指令": "show_commands",
    }

    def __init__(self, model_path: Path | None = None, language: str = "cn"):
        """初始化语音控制器

        Args:
            model_path: Vosk模型路径
            language: 语言 (cn/en)
        """
        if not VOSK_AVAILABLE:
            raise ImportError("Vosk未安装，请运行: pip install vosk sounddevice")

        self.language = language
        self.model_path = model_path or self._get_default_model_path(language)

        # 初始化组件
        self.model = None
        self.recognizer = None
        self.tts_engine = None

        # 指令系统
        self.commands: dict[str, Callable] = {}
        self.command_aliases = self.DEFAULT_COMMANDS.copy()

        # 音频流
        self.audio_queue = queue.Queue()
        self.is_listening = False
        self.listen_thread = None

        self._init_model()
        self._init_tts()

    def _get_default_model_path(self, language: str) -> Path:
        """获取默认模型路径"""
        base_path = Path("models/vosk")

        if language == "cn":
            return base_path / "vosk-model-cn-0.22"
        else:
            return base_path / "vosk-model-en-us-0.22"

    def _init_model(self):
        """初始化Vosk模型"""
        try:
            if not self.model_path.exists():
                logger.error(f"Vosk模型不存在: {self.model_path}")
                logger.info("请下载模型:")
                logger.info(
                    "  中文: https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip"
                )
                logger.info(
                    "  英文: https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"
                )
                raise FileNotFoundError(f"模型不存在: {self.model_path}")

            self.model = Model(str(self.model_path))
            self.recognizer = KaldiRecognizer(self.model, 16000)
            self.recognizer.SetWords(True)

            logger.info(f"成功加载Vosk模型: {self.model_path}")

        except Exception as e:
            logger.error(f"初始化Vosk模型失败: {e}")
            raise

    def _init_tts(self):
        """初始化文本转语音"""
        if not TTS_AVAILABLE:
            logger.warning("pyttsx3不可用，语音播报功能受限")
            return

        try:
            self.tts_engine = pyttsx3.init()

            # 配置语音
            voices = self.tts_engine.getProperty("voices")

            # 选择中文语音（如果可用）
            if self.language == "cn":
                for voice in voices:
                    if "chinese" in voice.name.lower() or "zh" in voice.id.lower():
                        self.tts_engine.setProperty("voice", voice.id)
                        break

            # 设置语速
            self.tts_engine.setProperty("rate", 150)  # 适中语速

            logger.info("成功初始化语音合成引擎")

        except Exception as e:
            logger.error(f"初始化TTS失败: {e}")

    def register_command(
        self, command_text: str, callback: Callable, aliases: list[str] | None = None
    ):
        """注册语音指令

        Args:
            command_text: 指令文本
            callback: 回调函数
            aliases: 指令别名列表
        """
        self.commands[command_text] = callback

        # 注册别名
        if aliases:
            for alias in aliases:
                self.command_aliases[alias] = command_text

        logger.debug(f"注册指令: {command_text}")

    def start_listening(self):
        """开始语音监听"""
        if self.is_listening:
            logger.warning("已在监听中")
            return

        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()

        logger.info("开始语音监听")
        self.speak("语音控制已启动")

    def stop_listening(self):
        """停止语音监听"""
        self.is_listening = False

        if self.listen_thread:
            self.listen_thread.join(timeout=2.0)

        logger.info("停止语音监听")

    def _listen_loop(self):
        """监听循环"""
        try:
            with sd.RawInputStream(
                samplerate=16000,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=self._audio_callback,
            ):
                while self.is_listening:
                    # 从队列获取音频数据
                    data = self.audio_queue.get()

                    # 语音识别
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "")

                        if text:
                            logger.info(f"识别到: {text}")
                            self._process_command(text)

        except Exception as e:
            logger.error(f"监听循环错误: {e}")
            self.is_listening = False

    def _audio_callback(self, indata, _frames, _time, status):
        """音频输入回调"""
        if status:
            logger.warning(f"音频状态: {status}")

        # 将音频数据放入队列
        self.audio_queue.put(bytes(indata))

    def _process_command(self, text: str):
        """处理识别到的指令

        Args:
            text: 识别文本
        """
        # 查找匹配的指令
        command_key = None

        # 精确匹配
        if text in self.commands:
            command_key = text
        elif text in self.command_aliases:
            command_key = self.command_aliases[text]
        else:
            # 模糊匹配
            for cmd in self.commands:
                if cmd in text or text in cmd:
                    command_key = cmd
                    break

        # 执行指令
        if command_key and command_key in self.commands:
            try:
                logger.info(f"执行指令: {command_key}")
                self.commands[command_key]()
                self.speak(f"已执行: {command_key}")
            except Exception as e:
                logger.error(f"执行指令失败: {e}")
                self.speak("指令执行失败")
        else:
            logger.debug(f"未识别的指令: {text}")
            # 不播报，避免干扰

    def speak(self, text: str, wait: bool = False):
        """语音播报

        Args:
            text: 播报文本
            wait: 是否等待播报完成
        """
        if not self.tts_engine:
            logger.debug(f"无TTS引擎，跳过播报: {text}")
            return

        try:
            self.tts_engine.say(text)

            if wait:
                self.tts_engine.runAndWait()
            else:
                # 异步播报
                threading.Thread(target=self.tts_engine.runAndWait, daemon=True).start()

            logger.debug(f"播报: {text}")

        except Exception as e:
            logger.error(f"语音播报失败: {e}")

    def get_available_commands(self) -> list[str]:
        """获取可用指令列表"""
        return list(self.commands.keys())

    def test_recognition(self, duration: int = 5):
        """测试语音识别

        Args:
            duration: 测试时长(秒)
        """
        logger.info(f"开始{duration}秒语音识别测试...")
        logger.info("请说话...")

        import time

        with sd.RawInputStream(
            samplerate=16000, blocksize=8000, dtype="int16", channels=1
        ) as stream:
            start_time = time.time()

            while time.time() - start_time < duration:
                data = stream.read(8000)[0]

                if self.recognizer.AcceptWaveform(bytes(data)):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "")

                    if text:
                        logger.info(f"识别到: {text}")

        # 最终结果
        final = json.loads(self.recognizer.FinalResult())
        if final.get("text"):
            logger.info(f"最终: {final['text']}")

        logger.info("测试完成")


# 便捷函数
def create_experiment_controller(model_path: Path | None = None) -> VoiceController:
    """创建实验语音控制器

    Args:
        model_path: 模型路径

    Returns:
        VoiceController实例
    """
    controller = VoiceController(model_path=model_path)

    # 注册实验指令
    def start_exp():
        logger.info("▶️ 开始实验")

    def stop_exp():
        logger.info("⏹️ 停止实验")

    def add_reagent():
        logger.info("🧪 添加试剂")

    def record_data():
        logger.info("📝 记录数据")

    controller.register_command("开始实验", start_exp, ["开始", "启动实验"])
    controller.register_command("停止实验", stop_exp, ["停止", "结束实验"])
    controller.register_command("添加试剂", add_reagent, ["加试剂"])
    controller.register_command("记录数据", record_data, ["记录", "保存数据"])

    return controller


def check_vosk_available() -> bool:
    """检查Vosk是否可用"""
    return VOSK_AVAILABLE and TTS_AVAILABLE


# 示例用法
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)

    # 检查依赖
    if not check_vosk_available():
        logger.info("❌ 语音功能不可用")
        logger.info("\n请安装依赖:")
        logger.info("  pip install vosk sounddevice pyttsx3")
        logger.info("\n然后下载模型:")
        logger.info(
            "  中文: https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip"
        )
        logger.info("  解压到: models/vosk/vosk-model-cn-0.22/")
        sys.exit(1)

    logger.info("✅ 语音功能可用\n")

    # 创建控制器
    try:
        controller = create_experiment_controller()

        # 测试语音识别
        print("=" * 60)
        logger.info("语音识别测试")
        print("=" * 60)
        logger.info("\n请说出以下任意指令:")
        logger.info("- 开始实验")
        logger.info("- 停止实验")
        logger.info("- 添加试剂")
        logger.info("- 记录数据")
        print()

        controller.test_recognition(duration=10)

        # 测试语音播报
        print("\n" + "=" * 60)
        logger.info("语音播报测试")
        print("=" * 60)
        controller.speak("这是语音播报测试", wait=True)
        logger.info("✅ 播报完成")

    except FileNotFoundError as e:
        logger.info(f"\n❌ {e}")
        logger.info("\n请下载并解压Vosk模型到正确位置")
    except Exception as e:
        logger.info(f"\n❌ 错误: {e}")
