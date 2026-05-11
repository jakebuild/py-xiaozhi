"""倒计时器工具管理器.

负责倒计时器工具的Initialization、Configuration和MCP工具Register
"""

from typing import Any, Dict

from src.utils.logging_config import get_logger

from .tools import (
    cancel_countdown_timer,
    get_active_countdown_timers,
    start_countdown_timer,
)

logger = get_logger(__name__)


class TimerToolsManager:
    """
    倒计时器工具管理器.
    """

    def __init__(self):
        """
        Initialization倒计时器工具管理器.
        """
        self._initialized = False
        logger.info("[TimerManager] 倒计时器工具管理器Initialization")

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        Initialization并Register所有倒计时器工具.
        """
        try:
            logger.info("[TimerManager] 开始Register倒计时器工具")

            # RegisterStart倒计时工具
            self._register_start_countdown_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Register取消倒计时工具
            self._register_cancel_countdown_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # RegisterGet活动倒计时工具
            self._register_get_active_timers_tool(add_tool, PropertyList)

            self._initialized = True
            logger.info("[TimerManager] 倒计时器工具RegisterComplete")

        except Exception as e:
            logger.error(f"[TimerManager] 倒计时器工具RegisterFailure: {e}", exc_info=True)
            raise

    def _register_start_countdown_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        RegisterStart倒计时工具.
        """
        timer_props = PropertyList(
            [
                Property(
                    "command",
                    PropertyType.STRING,
                ),
                Property(
                    "delay",
                    PropertyType.INTEGER,
                    default_value=5,
                    min_value=1,
                    max_value=3600,  # 最大1小时
                ),
                Property(
                    "description",
                    PropertyType.STRING,
                    default_value="",
                ),
            ]
        )

        add_tool(
            (
                "timer.start_countdown",
                "Start a countdown timer that will execute an MCP tool after a specified delay. "
                "The command should be a JSON string containing MCP tool name and arguments. "
                'For example: \'{"name": "self.audio_speaker.set_volume", "arguments": {"volume": 50}}\' '
                "Use this when the user wants to: \n"
                "1. Set a timer to control system settings (volume, device status, etc.) \n"
                "2. Schedule delayed MCP tool executions \n"
                "3. Create reminders with automatic tool calls \n"
                "The timer will return a timer_id that can be used to cancel it later.",
                timer_props,
                start_countdown_timer,
            )
        )
        logger.debug("[TimerManager] RegisterStart倒计时工具Success")

    def _register_cancel_countdown_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        Register取消倒计时工具.
        """
        cancel_props = PropertyList(
            [
                Property(
                    "timer_id",
                    PropertyType.INTEGER,
                )
            ]
        )

        add_tool(
            (
                "timer.cancel_countdown",
                "Cancel an active countdown timer by its ID. "
                "Use this when the user wants to: \n"
                "1. Cancel a previously set timer \n"
                "2. Stop a scheduled action before it executes \n"
                "You need the timer_id which is returned when starting a countdown.",
                cancel_props,
                cancel_countdown_timer,
            )
        )
        logger.debug("[TimerManager] Register取消倒计时工具Success")

    def _register_get_active_timers_tool(self, add_tool, PropertyList):
        """
        RegisterGet活动倒计时工具.
        """
        add_tool(
            (
                "timer.get_active_timers",
                "Get information about all currently active countdown timers. "
                "Returns details including timer IDs, remaining time, commands to execute, "
                "and progress for each active timer. "
                "Use this when the user wants to: \n"
                "1. Check what timers are currently running \n"
                "2. See remaining time for active timers \n"
                "3. Get timer IDs for cancellation \n"
                "4. Monitor timer progress and status",
                PropertyList(),
                get_active_countdown_timers,
            )
        )
        logger.debug("[TimerManager] RegisterGet活动倒计时工具Success")

    def is_initialized(self) -> bool:
        """
        检查管理器是否已Initialization.
        """
        return self._initialized

    def get_status(self) -> Dict[str, Any]:
        """
        Get管理器状态.
        """
        return {
            "initialized": self._initialized,
            "tools_count": 3,  # 当前Register的工具数量
            "available_tools": [
                "start_countdown",
                "cancel_countdown",
                "get_active_timers",
            ],
        }


# 全局管理器实例
_timer_tools_manager = None


def get_timer_manager() -> TimerToolsManager:
    """
    Get倒计时器工具管理器单例.
    """
    global _timer_tools_manager
    if _timer_tools_manager is None:
        _timer_tools_manager = TimerToolsManager()
        logger.debug("[TimerManager] 创建倒计时器工具管理器实例")
    return _timer_tools_manager
