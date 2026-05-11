"""统一的应用程序Start器.

根据系统自动选择对应的Start器实现
"""

import asyncio
import platform
from typing import Any, Dict, Optional

from src.utils.logging_config import get_logger

from .utils import find_best_matching_app

logger = get_logger(__name__)


async def launch_application(args: Dict[str, Any]) -> bool:
    """Start应用程序.

    Args:
        args: 包含应用程序名称的参数字典
            - app_name: 应用程序名称

    Returns:
        bool: Start是否Success
    """
    try:
        app_name = args["app_name"]
        logger.info(f"[AppLauncher] 尝试Start应用程序: {app_name}")

        # 首先尝试通过扫描找到精确匹配的应用程序
        matched_app = await _find_matching_application(app_name)
        if matched_app:
            logger.info(
                f"[AppLauncher] 找到匹配的应用程序: {matched_app.get('display_name', matched_app.get('name', ''))}"
            )
            # 根据应用程序类型使用不同的Start方法
            success = await _launch_matched_app(matched_app, app_name)
        else:
            # 如果没有找到匹配，使用原来的方法
            logger.info(f"[AppLauncher] 未找到精确匹配，使用原始名称: {app_name}")
            success = await _launch_by_name(app_name)

        if success:
            logger.info(f"[AppLauncher] SuccessStart应用程序: {app_name}")
        else:
            logger.warning(f"[AppLauncher] Start应用程序Failure: {app_name}")

        return success

    except KeyError:
        logger.error("[AppLauncher] 缺少app_name参数")
        return False
    except Exception as e:
        logger.error(f"[AppLauncher] Start应用程序Failure: {e}", exc_info=True)
        return False


async def _find_matching_application(app_name: str) -> Optional[Dict[str, Any]]:
    """通过扫描找到匹配的应用程序.

    Args:
        app_name: 要查找的应用程序名称

    Returns:
        匹配的应用程序信息，如果没找到则返回None
    """
    try:
        # 使用统一的匹配逻辑
        matched_app = await find_best_matching_app(app_name, "installed")

        if matched_app:
            logger.info(
                f"[AppLauncher] 通过统一匹配找到应用: {matched_app.get('display_name', matched_app.get('name', ''))}"
            )

        return matched_app

    except Exception as e:
        logger.warning(f"[AppLauncher] 查找匹配应用程序时出错: {e}")
        return None


async def _launch_matched_app(matched_app: Dict[str, Any], original_name: str) -> bool:
    """Start匹配到的应用程序.

    Args:
        matched_app: 匹配的应用程序信息
        original_name: 原始应用程序名称

    Returns:
        bool: Start是否Success
    """
    try:
        app_type = matched_app.get("type", "unknown")
        app_path = matched_app.get("path", matched_app.get("name", original_name))

        system = platform.system()

        if system == "Windows":
            # Windows系统特殊处理
            if app_type == "uwp":
                # UWP应用使用特殊的Start方法
                from .windows.launcher import launch_uwp_app_by_path

                return await asyncio.to_thread(launch_uwp_app_by_path, app_path)
            elif app_type == "shortcut" and app_path.endswith(".lnk"):
                # 快捷方式文件
                from .windows.launcher import launch_shortcut

                return await asyncio.to_thread(launch_shortcut, app_path)

        # 常规应用程序Start
        return await _launch_by_name(app_path)

    except Exception as e:
        logger.error(f"[AppLauncher] Start匹配应用Failure: {e}")
        return False


async def _launch_by_name(app_name: str) -> bool:
    """根据名称Start应用程序.

    Args:
        app_name: 应用程序名称或路径

    Returns:
        bool: Start是否Success
    """
    try:
        system = platform.system()

        if system == "Windows":
            from .windows.launcher import launch_application

            return await asyncio.to_thread(launch_application, app_name)
        elif system == "Darwin":  # macOS
            from .mac.launcher import launch_application

            return await asyncio.to_thread(launch_application, app_name)
        elif system == "Linux":
            from .linux.launcher import launch_application

            return await asyncio.to_thread(launch_application, app_name)
        else:
            logger.error(f"[AppLauncher] 不支持的操作系统: {system}")
            return False

    except Exception as e:
        logger.error(f"[AppLauncher] Start应用程序Failure: {e}")
        return False


def get_system_launcher():
    """根据当前系统Get对应的Start器模块.

    Returns:
        对应系统的Start器模块
    """
    system = platform.system()

    if system == "Darwin":  # macOS
        from .mac import launcher

        return launcher
    elif system == "Windows":  # Windows
        from .windows import launcher

        return launcher
    elif system == "Linux":  # Linux
        from .linux import launcher

        return launcher
    else:
        logger.warning(f"[AppLauncher] 不支持的系统: {system}")
        return None
