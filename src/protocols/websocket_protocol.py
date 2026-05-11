import asyncio
import json
import ssl
import time

import websockets

from src.constants.constants import AudioConfig
from src.protocols.protocol import Protocol
from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

ssl_context = ssl._create_unverified_context()

logger = get_logger(__name__)


class WebsocketProtocol(Protocol):
    def __init__(self):
        super().__init__()
        # GetConfiguration管理器实例
        self.config = ConfigManager.get_instance()
        self.websocket = None
        self.connected = False
        self.hello_received = None  # Initialization时先设为 None
        # 消息处理任务引用，便于在Close时取消
        self._message_task = None

        # Connect健康状态监测
        self._last_ping_time = None
        self._last_pong_time = None
        self._ping_interval = 30.0  # 心跳间隔（秒）
        self._ping_timeout = 10.0  # pingTimeout时间（秒）
        self._heartbeat_task = None
        self._connection_monitor_task = None

        # Connect状态标志
        self._is_closing = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 0  # 默认不Reconnect
        self._auto_reconnect_enabled = False  # 默认Close自动Reconnect

        self.WEBSOCKET_URL = self.config.get_config(
            "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL"
        )
        access_token = self.config.get_config(
            "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_ACCESS_TOKEN"
        )
        device_id = self.config.get_config("SYSTEM_OPTIONS.DEVICE_ID")
        client_id = self.config.get_config("SYSTEM_OPTIONS.CLIENT_ID")

        self.HEADERS = {
            "Authorization": f"Bearer {access_token}",
            "Protocol-Version": "1",
            "Device-Id": device_id,  # Get设备MAC地址
            "Client-Id": client_id,
        }

    async def connect(self) -> bool:
        """
        Connected to WebSocket server.
        """
        if self._is_closing:
            logger.warning("Connect正在Close中，取消新的Connect尝试")
            return False

        try:
            # 在Connect时创建 Event，确保在正确的事件循环中
            self.hello_received = asyncio.Event()

            # 判断是否应该使用 SSL
            current_ssl_context = None
            if self.WEBSOCKET_URL.startswith("wss://"):
                current_ssl_context = ssl_context

            # 建立WebSocketConnect (兼容不同Python版本的写法)
            try:
                # 新的写法 (在Python 3.11+版本中)
                self.websocket = await websockets.connect(
                    uri=self.WEBSOCKET_URL,
                    ssl=current_ssl_context,
                    additional_headers=self.HEADERS,
                    ping_interval=20,  # 使用websockets自己的心跳，20秒间隔
                    ping_timeout=20,  # pingTimeout20秒
                    close_timeout=10,  # CloseTimeout10秒
                    max_size=10 * 1024 * 1024,  # 最大消息10MB
                    compression=None,  # 禁用压缩以提高稳定性
                )
            except TypeError:
                # 旧的写法 (在较早的Python版本中)
                self.websocket = await websockets.connect(
                    self.WEBSOCKET_URL,
                    ssl=current_ssl_context,
                    extra_headers=self.HEADERS,
                    ping_interval=20,  # 使用websockets自己的心跳
                    ping_timeout=20,  # pingTimeout20秒
                    close_timeout=10,  # CloseTimeout10秒
                    max_size=10 * 1024 * 1024,  # 最大消息10MB
                    compression=None,  # 禁用压缩
                )

            # Start消息处理循环（Save任务引用，Close时可取消）
            self._message_task = asyncio.create_task(self._message_handler())

            # 注释掉自定义心跳，使用websockets内置的心跳机制
            # self._start_heartbeat()

            # StartConnect监控
            self._start_connection_monitor()

            # 发送客户端hello消息
            hello_message = {
                "type": "hello",
                "version": 1,
                "features": {
                    "mcp": True,
                },
                "transport": "websocket",
                "audio_params": {
                    "format": "opus",
                    "sample_rate": AudioConfig.INPUT_SAMPLE_RATE,
                    "channels": AudioConfig.CHANNELS,
                    "frame_duration": AudioConfig.FRAME_DURATION,
                },
            }
            await self.send_text(json.dumps(hello_message))

            # 等待服务器hello响应
            try:
                await asyncio.wait_for(self.hello_received.wait(), timeout=10.0)
                self.connected = True
                self._reconnect_attempts = 0  # 重置Reconnect计数
                logger.info("已Connected to WebSocket server")

                # 通知Connect状态变化
                if self._on_connection_state_changed:
                    self._on_connection_state_changed(True, "ConnectSuccess")

                return True
            except asyncio.TimeoutError:
                logger.error("等待服务器hello响应Timeout")
                await self._cleanup_connection()
                if self._on_network_error:
                    self._on_network_error("等待响应Timeout")
                return False

        except Exception as e:
            logger.error(f"WebSocketConnection failed: {e}")
            await self._cleanup_connection()
            if self._on_network_error:
                self._on_network_error(f"无法Connect服务: {str(e)}")
            return False

    def _start_heartbeat(self):
        """
        Start心跳检测任务.
        """
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    def _start_connection_monitor(self):
        """
        StartConnect监控任务.
        """
        if (
            self._connection_monitor_task is None
            or self._connection_monitor_task.done()
        ):
            self._connection_monitor_task = asyncio.create_task(
                self._connection_monitor()
            )

    async def _heartbeat_loop(self):
        """
        心跳检测循环.
        """
        try:
            while self.websocket and not self._is_closing:
                await asyncio.sleep(self._ping_interval)

                if self.websocket and not self._is_closing:
                    try:
                        self._last_ping_time = time.time()
                        # 发送ping并等待pong响应
                        pong_waiter = await self.websocket.ping()
                        logger.debug("发送心跳ping")

                        # 等待pong响应
                        try:
                            await asyncio.wait_for(
                                pong_waiter, timeout=self._ping_timeout
                            )
                            self._last_pong_time = time.time()
                            logger.debug("收到心跳pong响应")
                        except asyncio.TimeoutError:
                            logger.warning("心跳pong响应Timeout")
                            await self._handle_connection_loss("心跳pongTimeout")
                            break

                    except Exception as e:
                        logger.error(f"发送心跳Failure: {e}")
                        await self._handle_connection_loss("心跳发送Failure")
                        break
        except asyncio.CancelledError:
            logger.debug("心跳任务被取消")
        except Exception as e:
            logger.error(f"心跳循环Exception: {e}")

    async def _connection_monitor(self):
        """
        Connect健康状态监控.
        """
        try:
            while self.websocket and not self._is_closing:
                await asyncio.sleep(5)  # 每5秒检查一次

                # 检查Connect状态
                if self.websocket:
                    if self.websocket.close_code is not None:
                        logger.warning("检测到WebSocketConnectClosed")
                        await self._handle_connection_loss("ConnectClosed")
                        break

        except asyncio.CancelledError:
            logger.debug("Connect监控任务被取消")
        except Exception as e:
            logger.error(f"Connect监控Exception: {e}")

    async def _handle_connection_loss(self, reason: str):
        """
        处理Connect丢失.
        """
        logger.warning(f"Connect丢失: {reason}")

        # UpdateConnect状态
        was_connected = self.connected
        self.connected = False

        # 通知Connect状态变化
        if self._on_connection_state_changed and was_connected:
            try:
                self._on_connection_state_changed(False, reason)
            except Exception as e:
                logger.error(f"调用Connect状态变化回调Failure: {e}")

        # CleanupConnect
        await self._cleanup_connection()

        # 通知音频通道Close
        if self._on_audio_channel_closed:
            try:
                await self._on_audio_channel_closed()
            except Exception as e:
                logger.error(f"调用音频通道Close回调Failure: {e}")

        # 只有在启用自动Reconnect且未手动Close时才尝试Reconnect
        if (
            not self._is_closing
            and self._auto_reconnect_enabled
            and self._reconnect_attempts < self._max_reconnect_attempts
        ):
            await self._attempt_reconnect(reason)
        else:
            # 通知网络Error
            if self._on_network_error:
                if (
                    self._auto_reconnect_enabled
                    and self._reconnect_attempts >= self._max_reconnect_attempts
                ):
                    self._on_network_error(f"Connect丢失且ReconnectFailure: {reason}")
                else:
                    self._on_network_error(f"Connect丢失: {reason}")

    async def _attempt_reconnect(self, original_reason: str):
        """
        尝试自动Reconnect.
        """
        self._reconnect_attempts += 1

        # 通知开始Reconnect
        if self._on_reconnecting:
            try:
                self._on_reconnecting(
                    self._reconnect_attempts, self._max_reconnect_attempts
                )
            except Exception as e:
                logger.error(f"调用Reconnect回调Failure: {e}")

        logger.info(
            f"尝试自动Reconnect ({self._reconnect_attempts}/{self._max_reconnect_attempts})"
        )

        # 等待一段时间后Reconnect
        await asyncio.sleep(min(self._reconnect_attempts * 2, 30))  # 指数退避，最大30秒

        try:
            success = await self.connect()
            if success:
                logger.info("自动ReconnectSuccess")
                # 通知Connect状态变化
                if self._on_connection_state_changed:
                    self._on_connection_state_changed(True, "ReconnectSuccess")
            else:
                logger.warning(
                    f"自动ReconnectFailure ({self._reconnect_attempts}/{self._max_reconnect_attempts})"
                )
                # 如果还能重试，不立即报错
                if self._reconnect_attempts >= self._max_reconnect_attempts:
                    if self._on_network_error:
                        self._on_network_error(
                            f"ReconnectFailure，已达到最大Reconnect次数: {original_reason}"
                        )
        except Exception as e:
            logger.error(f"Reconnect过程中出错: {e}")
            if self._reconnect_attempts >= self._max_reconnect_attempts:
                if self._on_network_error:
                    self._on_network_error(f"ReconnectException: {str(e)}")

    def enable_auto_reconnect(self, enabled: bool = True, max_attempts: int = 5):
        """启用或禁用自动Reconnect功能.

        Args:
            enabled: 是否启用自动Reconnect
            max_attempts: 最大Reconnect尝试次数
        """
        self._auto_reconnect_enabled = enabled
        if enabled:
            self._max_reconnect_attempts = max_attempts
            logger.info(f"启用自动Reconnect，最大尝试次数: {max_attempts}")
        else:
            self._max_reconnect_attempts = 0
            logger.info("禁用自动Reconnect")

    def get_connection_info(self) -> dict:
        """Getting connection info.

        Returns:
            dict: 包含Connect状态、Reconnect次数等信息的字典
        """
        return {
            "connected": self.connected,
            "websocket_closed": (
                self.websocket.close_code is not None if self.websocket else True
            ),
            "is_closing": self._is_closing,
            "auto_reconnect_enabled": self._auto_reconnect_enabled,
            "reconnect_attempts": self._reconnect_attempts,
            "max_reconnect_attempts": self._max_reconnect_attempts,
            "last_ping_time": self._last_ping_time,
            "last_pong_time": self._last_pong_time,
            "websocket_url": self.WEBSOCKET_URL,
        }

    async def _message_handler(self):
        """
        处理接收到的WebSocket消息.
        """
        try:
            async for message in self.websocket:
                if self._is_closing:
                    break

                try:
                    if isinstance(message, str):
                        try:
                            data = json.loads(message)
                            msg_type = data.get("type")
                            if msg_type == "hello":
                                # 处理服务器 hello 消息
                                await self._handle_server_hello(data)
                            else:
                                if self._on_incoming_json:
                                    self._on_incoming_json(data)
                        except json.JSONDecodeError as e:
                            logger.error(f"无效的JSON消息: {message}, Error: {e}")
                    elif isinstance(message, bytes):
                        # 二进制消息，可能是音频
                        if self._on_incoming_audio:
                            self._on_incoming_audio(message)
                except Exception as e:
                    # 处理单个消息的Error，但继续处理其他消息
                    logger.error(f"处理消息时出错: {e}", exc_info=True)
                    continue

        except asyncio.CancelledError:
            logger.debug("消息处理任务被取消")
            return
        except websockets.ConnectionClosed as e:
            if not self._is_closing:
                logger.info(f"WebSocketConnectClosed: {e}")
                await self._handle_connection_loss(f"ConnectClose: {e.code} {e.reason}")
        except websockets.ConnectionClosedError as e:
            if not self._is_closing:
                logger.info(f"WebSocketConnectErrorClose: {e}")
                await self._handle_connection_loss(f"ConnectError: {e.code} {e.reason}")
        except websockets.InvalidState as e:
            logger.error(f"WebSocket状态无效: {e}")
            await self._handle_connection_loss("Connect状态Exception")
        except ConnectionResetError:
            logger.warning("Connect被重置")
            await self._handle_connection_loss("Connect被重置")
        except OSError as e:
            logger.error(f"网络I/OError: {e}")
            await self._handle_connection_loss("网络I/OError")
        except Exception as e:
            logger.error(f"消息处理循环Exception: {e}", exc_info=True)
            await self._handle_connection_loss(f"消息处理Exception: {str(e)}")

    async def send_audio(self, data: bytes):
        """
        发送音频数据.
        """
        if not self.is_audio_channel_opened():
            return

        try:
            await self.websocket.send(data)
        except websockets.ConnectionClosed as e:
            logger.warning(f"发送音频时ConnectClosed: {e}")
            await self._handle_connection_loss(f"发送音频Failure: {e.code} {e.reason}")
        except websockets.ConnectionClosedError as e:
            logger.warning(f"发送音频时ConnectError: {e}")
            await self._handle_connection_loss(f"发送音频Error: {e.code} {e.reason}")
        except Exception as e:
            logger.error(f"发送音频数据Failure: {e}")
            # 不要在这里调用网络Error回调，让Connect处理器处理
            await self._handle_connection_loss(f"发送音频Exception: {str(e)}")

    async def send_text(self, message: str):
        """
        Send Text消息.
        """
        if not self.websocket or self._is_closing:
            logger.warning("WebSocketDisconnected或正在Close，无法发送消息")
            return

        try:
            await self.websocket.send(message)
        except websockets.ConnectionClosed as e:
            logger.warning(f"Send Text时ConnectClosed: {e}")
            await self._handle_connection_loss(f"Send TextFailure: {e.code} {e.reason}")
        except websockets.ConnectionClosedError as e:
            logger.warning(f"Send Text时ConnectError: {e}")
            await self._handle_connection_loss(f"Send TextError: {e.code} {e.reason}")
        except Exception as e:
            logger.error(f"Send Text消息Failure: {e}")
            await self._handle_connection_loss(f"Send TextException: {str(e)}")

    def is_audio_channel_opened(self) -> bool:
        """检查音频通道是否打开.

        更准确地检查Connect状态，包括WebSocket的实际状态
        """
        if not self.websocket or not self.connected or self._is_closing:
            return False

        # 检查WebSocket的实际状态
        try:
            return self.websocket.close_code is None
        except Exception:
            return False

    async def open_audio_channel(self) -> bool:
        """建立 WebSocket Connect.

        如果尚Disconnected,则创建新的 WebSocket Connect
        Returns:
            bool: Connect是否Success
        """
        if not self.is_audio_channel_opened():
            return await self.connect()
        return True

    async def _handle_server_hello(self, data: dict):
        """
        处理服务器的 hello 消息.
        """
        try:
            # 验证传输方式
            transport = data.get("transport")
            if not transport or transport != "websocket":
                logger.error(f"不支持的传输方式: {transport}")
                return

            # 设置 hello 接收事件
            self.hello_received.set()

            # 通知音频通道已打开
            if self._on_audio_channel_opened:
                await self._on_audio_channel_opened()

            logger.info("Success处理服务器 hello 消息")

        except Exception as e:
            logger.error(f"处理服务器 hello 消息时出错: {e}")
            if self._on_network_error:
                self._on_network_error(f"处理服务器响应Failure: {str(e)}")

    async def _cleanup_connection(self):
        """
        Cleaning up connection resources.
        """
        self.connected = False

        # 取消消息处理任务，防止事件循环Exit后仍有挂起等待
        if self._message_task and not self._message_task.done():
            self._message_task.cancel()
            try:
                await self._message_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"等待消息任务取消时Exception: {e}")
        self._message_task = None

        # 取消心跳任务
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # 取消Connect监控任务
        if self._connection_monitor_task and not self._connection_monitor_task.done():
            self._connection_monitor_task.cancel()
            try:
                await self._connection_monitor_task
            except asyncio.CancelledError:
                pass

        # CloseWebSocketConnect
        if self.websocket and self.websocket.close_code is None:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"CloseWebSocketConnect时出错: {e}")

        self.websocket = None
        self._last_ping_time = None
        self._last_pong_time = None

    async def close_audio_channel(self):
        """
        Close音频通道.
        """
        self._is_closing = True

        try:
            await self._cleanup_connection()

            if self._on_audio_channel_closed:
                await self._on_audio_channel_closed()

        except Exception as e:
            logger.error(f"Close音频通道Failure: {e}")
        finally:
            self._is_closing = False
