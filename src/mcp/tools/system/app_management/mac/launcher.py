"""macOS系统应用程序Start器.

提供macOS平台下的应用程序Start功能
"""

import os
import subprocess

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def launch_application(app_name: str) -> bool:
    """在macOS上Start应用程序.

    Args:
        app_name: 应用程序名称

    Returns:
        bool: Start是否Success
    """
    try:
        logger.info(f"[MacLauncher] Start应用程序: {app_name}")

        # 方法1: 使用open -a命令
        try:
            subprocess.Popen(["open", "-a", app_name])
            logger.info(f"[MacLauncher] 使用open -aSuccessStart: {app_name}")
            return True
        except (OSError, subprocess.SubprocessError):
            logger.debug(f"[MacLauncher] open -aStartFailure: {app_name}")

        # 方法2: 直接使用应用程序名称
        try:
            subprocess.Popen([app_name])
            logger.info(f"[MacLauncher] 直接StartSuccess: {app_name}")
            return True
        except (OSError, subprocess.SubprocessError):
            logger.debug(f"[MacLauncher] 直接StartFailure: {app_name}")

        # 方法3: 尝试Applications目录
        app_path = f"/Applications/{app_name}.app"
        if os.path.exists(app_path):
            subprocess.Popen(["open", app_path])
            logger.info(f"[MacLauncher] 通过Applications目录StartSuccess: {app_name}")
            return True

        # 方法4: 使用osascriptStart
        script = f'tell application "{app_name}" to activate'
        subprocess.Popen(["osascript", "-e", script])
        logger.info(f"[MacLauncher] 使用osascriptStartSuccess: {app_name}")
        return True

    except Exception as e:
        logger.error(f"[MacLauncher] macOSStartFailure: {e}")
        return False
