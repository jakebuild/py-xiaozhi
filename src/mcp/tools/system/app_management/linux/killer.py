"""Linux系统应用程序Close器.

提供Linux平台下的应用程序Close功能
"""

import subprocess
from typing import Any, Dict, List

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def list_running_applications(filter_name: str = "") -> List[Dict[str, Any]]:
    """
    列出Linux上正在运行的应用程序.
    """
    apps = []

    try:
        # 使用ps命令Get进程信息
        result = subprocess.run(
            ["ps", "-eo", "pid,ppid,comm,command", "--no-headers"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")

            for line in lines:
                parts = line.strip().split(None, 3)
                if len(parts) >= 4:
                    pid, ppid, comm, command = parts

                    # 过滤GUI应用程序
                    is_gui_app = (
                        not command.startswith("/usr/bin/")
                        and not command.startswith("/bin/")
                        and not command.startswith("[")  # 内核线程
                        and len(comm) > 2
                    )

                    if is_gui_app:
                        app_name = comm

                        # 应用过滤条件
                        if not filter_name or filter_name.lower() in app_name.lower():
                            apps.append(
                                {
                                    "pid": int(pid),
                                    "ppid": int(ppid),
                                    "name": app_name,
                                    "display_name": app_name,
                                    "command": command,
                                    "type": "application",
                                }
                            )

    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        logger.warning(f"[LinuxKiller] Linux进程扫描Failure: {e}")

    return apps


def kill_application(pid: int, force: bool) -> bool:
    """
    在Linux上Close应用程序.
    """
    try:
        logger.info(
            f"[LinuxKiller] 尝试CloseLinux应用程序，PID: {pid}, 强制Close: {force}"
        )

        if force:
            # 强制Close (SIGKILL)
            result = subprocess.run(
                ["kill", "-9", str(pid)], capture_output=True, timeout=5
            )
        else:
            # 正常Close (SIGTERM)
            result = subprocess.run(
                ["kill", "-15", str(pid)], capture_output=True, timeout=5
            )

        success = result.returncode == 0

        if success:
            logger.info(f"[LinuxKiller] SuccessClose应用程序，PID: {pid}")
        else:
            logger.warning(f"[LinuxKiller] Failed to close application，PID: {pid}")

        return success

    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        logger.error(f"[LinuxKiller] LinuxFailed to close application: {e}")
        return False
