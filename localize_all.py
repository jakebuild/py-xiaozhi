import os

replacements = {
    # Core Framework & Logs
    "尝试创建Application的多个实例": "Attempting to create multiple Application instances",
    "Application是单例类，请使用get_instance()获取实例": "Application is a singleton class, use get_instance()",
    "初始化Application实例": "Initializing Application instance",
    "启动Application，protocol=%s": "Starting Application, protocol=%s",
    "应用运行失败": "Application failed to run",
    "正在中止，忽略重复的中止请求": "Aborting, ignoring duplicate request",
    "中止语音输出，原因:": "Aborting voice output, reason:",
    "正在关闭Application...": "Shutting down Application...",
    "Application 关闭完成": "Application shutdown complete",
    "设置设备状态:": "Set device state:",
    "协议连接已建立，按Ctrl+C退出": "Protocol connection established, press Ctrl+C to exit",
    "连接到WebSocket服务器": "Connected to WebSocket server",
    "协议连接就绪": "Protocol connection ready",
    "收到JSON消息:": "Received JSON message:",
    "收到文本:": "Received text:",
    "正在处理": "Processing",
    "唤醒词功能已禁用": "Wake word feature disabled",
    "日程提醒服务已启动": "Reminder service started",
    "今日无日程安排": "No schedule today",
    "开始日程提醒检查循环": "Starting reminder check loop",
    "清空音频队列，丢弃": "Clearing audio queue, discarding",
    "帧音频数据": "frames of audio data",
    "说话中发送打断": "Sending interruption while speaking",
    "TTS 播放完成": "TTS playback finished",
    "恢复音乐播放": "Resuming music playback",
    "关闭音频资源": "Closing audio resources",
    "关闭音频编解码器失败": "Failed to close audio codec",
    "音频线程回调": "Audio thread callback",
    "静默期内禁止发送音频": "Audio capture disabled during silent period",
    "收到工具调用请求!": "Received tool call request!",
    "尝试调用工具:": "Attempting to call tool:",
    "开始执行工具": "Starting tool execution",
    "工具执行成功": "Tool execution successful",
    "工具执行失败": "Tool execution failed",
    "发送成功响应:": "Sending success response:",
    "发送错误响应:": "Sending error response:",
    "发送回调未设置!": "Send callback not set!",
    "全局快捷键监听已启动": "Global shortcut listener started",
    "启动全局快捷键监听失败": "Failed to start global shortcut listener",
    "全局快捷键监听已停止": "Global shortcut listener stopped",
    "快捷键配置已重新加载": "Shortcut config reloaded",
    "重新加载快捷键配置失败": "Failed to reload shortcut config",

    # UI Labels
    "待命": "Idle",
    "聆听中...": "Listening...",
    "说话中...": "Speaking...",
    "连接: ": "Link: ",
    "已连接": "Connected",
    "未连接": "Disconnected",
    "状态: ": "Status: ",
    "表情: ": "Emotion: ",
    "文本: ": "Text: ",
    "输入: ": "Input: ",
    " 小智 AI 终端 ": " Xiaozhi AI Terminal ",
    "命令帮助": "Command Help",
    "可用命令": "Available Commands",
    "退出程序": "Quit",
    "显示帮助": "Help",
    "自动对话": "Auto Talk",
    "发送文本": "Send Text",

    # General Words
    "初始化": "Initialize",
    "配置": "Config",
    "成功": "Success",
    "失败": "Failure",
    "完成": "Complete",
    "关闭": "Close",
    "启动": "Start",
    "退出": "Exit",
    "停止": "Stop",
    "恢复": "Resume",
    "重启": "Restart",
    "加载": "Load",
    "解析": "Parse",
    "刷新": "Refresh",
    "重连": "Reconnect",
    "超时": "Timeout",
    "连接": "Connect",
    "断开": "Disconnect",
    "清理": "Cleanup",
    "获取": "Get",
    "搜索": "Search",
    "更新": "Update",
    "删除": "Delete",
    "保存": "Save",
    "注册": "Register",
    "注销": "Unregister",
}

def translate_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        return False
    
    original_content = content
    for cn, en in replacements.items():
        content = content.replace(cn, en)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    # Translate src files
    root_dir = 'src'
    modified_files = 0
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if translate_file(file_path):
                    modified_files += 1
                    print(f"Translated: {file_path}")
    
    # Translate face UI script
    if translate_file('xiaozhi_face_ui.py'):
        modified_files += 1
        print("Translated: xiaozhi_face_ui.py")
    
    print(f"\nTotal files translated: {modified_files}")

if __name__ == "__main__":
    main()
