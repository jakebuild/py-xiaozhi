import asyncio
import os
from typing import Any

from src.audio_codecs.audio_codec import AudioCodec
from src.plugins.base import Plugin
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# 常量Configuration
MAX_CONCURRENT_AUDIO_SENDS = 4


class AudioPlugin(Plugin):
    name = "audio"
    priority = 10  # 最高优先级，其他插件依赖 audio_codec

    def __init__(self) -> None:
        super().__init__()
        self.app = None
        self.codec: AudioCodec | None = None
        self._main_loop = None
        self._send_sem = asyncio.Semaphore(MAX_CONCURRENT_AUDIO_SENDS)
        self._in_silence_period = False  # 静默期标志，用于Prevent TTS trailing sound from being captured

    async def setup(self, app: Any) -> None:
        self.app = app
        self._main_loop = app._main_loop

        if os.getenv("XIAOZHI_DISABLE_AUDIO") == "1":
            return

        try:
            self.codec = AudioCodec()
            await self.codec.initialize()

            # 设置编码音频回调：直接发送，不走队列
            self.codec.set_encoded_callback(self._on_encoded_audio)

            # 暴露给应用，便于唤醒词插件使用
            self.app.audio_codec = self.codec
        except Exception as e:
            logger.error(f"音频插件InitializationFailure: {e}", exc_info=True)
            self.codec = None

    async def on_device_state_changed(self, state):
        """设备状态变化时Clearing audio queue.

        特别处理：进入 LISTENING 状态时，等待音频硬件输出完全Stop， 避免 TTS 尾音被麦克风捕获导致误触发。
        """
        if not self.codec:
            return

        from src.constants.constants import DeviceState

        # 如果进入监听状态，清空队列并等待硬件输出完全Stop
        if state == DeviceState.LISTENING:
            # 设置静默期标志，阻止麦克风音频发送
            self._in_silence_period = True
            try:
                # 等待硬件 DAC 输出Complete（50-100ms）+ 声波传播（20ms）+ 安全余量
                await asyncio.sleep(0.2)
            finally:
                # 清空和等待Complete后，解除静默期
                self._in_silence_period = False

    async def on_incoming_json(self, message: Any) -> None:
        """处理 TTS 事件，控制音乐播放.

        Args:
            message: JSON消息，包含 type 和 state 字段
        """
        if not isinstance(message, dict):
            return

        try:
            # 监听 TTS 状态变化，控制音乐播放
            if message.get("type") == "tts":
                state = message.get("state")
                if state == "start":
                    # TTS 开始：先Clearing audio queue，再暂停音乐
                    await self._pause_music_for_tts()
                elif state == "stop":
                    # TTS 结束：Resume music playback
                    await self._resume_music_after_tts()
                    await self.codec.clear_audio_queue()
        except Exception as e:
            logger.error(f"处理 TTS 事件Failure: {e}", exc_info=True)

    async def on_incoming_audio(self, data: bytes) -> None:
        """接收服务端返回的音频数据并播放.

        Args:
            data: 服务端返回的Opus编码音频数据
        """
        if self.codec:
            try:
                await self.codec.write_audio(data)
            except Exception as e:
                logger.debug(f"写入音频数据Failure: {e}")

    async def _pause_music_for_tts(self):
        """
        TTS 开始时：先Clearing audio queue，再暂停音乐.
        """
        try:
            if self.codec:
                await self.codec.clear_audio_queue()
                logger.debug("TTS 开始，已Clearing audio queue")

            try:
                from src.mcp.tools.music.music_player import get_music_player_instance

                music_player = get_music_player_instance()

                # 如果音乐正在播放且未暂停，则暂停
                if music_player.is_playing and not music_player.paused:
                    logger.info("TTS 开始，暂停音乐播放")
                    result = await music_player.pause(source="tts")
                    if result.get("status") != "success":
                        logger.warning(f"暂停音乐返回Exception: {result}")
            except Exception as e:
                logger.warning(f"暂停音乐Failure: {e}")

        except Exception as e:
            logger.error(f"TTS 开始处理Failure: {e}", exc_info=True)

    async def _resume_music_after_tts(self):
        """
        TTS 结束后：Resume music playback或Start延迟播放.
        """
        try:
            from src.mcp.tools.music.music_player import get_music_player_instance

            music_player = get_music_player_instance()

            if music_player._deferred_start_path:
                logger.info("TTS playback finished，Start延迟播放的音乐")
                # 直接调用内部方法，跳过TTS检查
                file_path = music_player._deferred_start_path
                start_pos = music_player._deferred_start_position
                music_player._deferred_start_path = None
                music_player._deferred_start_position = 0.0

                # 重新Start播放（此时TTS已结束，不会再延迟）
                await music_player._start_playback(file_path, start_pos)
                return

            if music_player.is_playing and music_player.paused:
                if music_player._pause_source == "tts":
                    logger.info("TTS playback finished，Resume music playback")
                    await music_player.resume()
                else:
                    logger.debug(
                        f"Music pause source: {music_player._pause_source}，No automatic recovery"
                    )
            else:
                logger.debug(
                    f"音乐Status: is_playing={music_player.is_playing}, "
                    f"paused={music_player.paused}, No need to restore"
                )
        except Exception as e:
            logger.error(f"Resume music playbackFailure: {e}", exc_info=True)

    async def shutdown(self) -> None:
        """
        Close and release audio resources.
        """
        # Stop音频消费者任务
        if self._audio_consumer_task and not self._audio_consumer_task.done():
            self._audio_consumer_task.cancel()
            try:
                await self._audio_consumer_task
            except asyncio.CancelledError:
                pass

        if self.codec:
            try:
                await self.codec.close()
            except Exception as e:
                logger.error(f"Failed to close audio codec: {e}", exc_info=True)
            finally:
                self.codec = None

        # 清空应用引用
        if self.app:
            self.app.audio_codec = None

    # -------------------------
    # 内部：直接发送录音音频（不走队列）
    # -------------------------
    def _on_encoded_audio(self, encoded_data: bytes) -> None:
        """
        Audio thread callback：切换到主循环并直接发送（参考旧版本）
        """
        try:
            if not self.app or not self._main_loop or not self.app.running:
                return
            if self._main_loop.is_closed():
                return
            self._main_loop.call_soon_threadsafe(
                self._schedule_send_audio, encoded_data
            )
        except Exception:
            pass

    def _schedule_send_audio(self, encoded_data: bytes) -> None:
        """
        在主事件循环中调度发送任务.
        """
        if not self.app or not self.app.running or not self.app.protocol:
            return

        async def _send():
            async with self._send_sem:
                try:
                    if not (
                        self.app.protocol
                        and self.app.protocol.is_audio_channel_opened()
                    ):
                        return
                    if self._should_send_microphone_audio():
                        await self.app.protocol.send_audio(encoded_data)
                except Exception:
                    pass

        # 创建任务但不等待，实现"发完即忘"
        self.app.spawn(_send(), name="audio:send")

    def _should_send_microphone_audio(self) -> bool:
        """
        委托给应用的统一状态机规则，并检查静默期标志.
        """
        try:
            # Prohibited sending audio during silent period（Prevent TTS trailing sound from being captured）
            if self._in_silence_period:
                return False
            return self.app and self.app.should_capture_audio()
        except Exception:
            return False
