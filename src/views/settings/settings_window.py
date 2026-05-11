import os
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog,
    QMessageBox,
    QPushButton,
    QTabWidget,
)

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger
from src.views.settings.components.audio import AudioWidget
from src.views.settings.components.camera import CameraWidget
from src.views.settings.components.shortcuts_settings import ShortcutsSettingsWidget
from src.views.settings.components.system_options import SystemOptionsWidget
from src.views.settings.components.wake_word import WakeWordWidget


class SettingsWindow(QDialog):
    """
    参数Configuration窗口.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.config_manager = ConfigManager.get_instance()

        # 组件引用
        self.system_options_tab = None
        self.wake_word_tab = None
        self.camera_tab = None
        self.audio_tab = None
        self.shortcuts_tab = None

        # UI控件
        self.ui_controls = {}

        # InitializationUI
        self._setup_ui()
        self._connect_events()

    def _setup_ui(self):
        """
        设置UI界面.
        """
        try:
            from PyQt5 import uic

            ui_path = Path(__file__).parent / "settings_window.ui"
            uic.loadUi(str(ui_path), self)

            # GetUI控件的引用
            self._get_ui_controls()

            # 添加各个组件选项卡
            self._add_component_tabs()

        except Exception as e:
            self.logger.error(f"设置UIFailure: {e}", exc_info=True)
            raise

    def _add_component_tabs(self):
        """
        添加各个组件选项卡.
        """
        try:
            # GetTabWidget
            tab_widget = self.findChild(QTabWidget, "tabWidget")
            if not tab_widget:
                self.logger.error("未找到TabWidget控件")
                return

            # 清空现有选项卡（如果有的话）
            tab_widget.clear()

            # 创建并添加系统选项组件
            self.system_options_tab = SystemOptionsWidget()
            tab_widget.addTab(self.system_options_tab, "系统选项")
            self.system_options_tab.settings_changed.connect(self._on_settings_changed)

            # 创建并添加唤醒词组件
            self.wake_word_tab = WakeWordWidget()
            tab_widget.addTab(self.wake_word_tab, "唤醒词")
            self.wake_word_tab.settings_changed.connect(self._on_settings_changed)

            # 创建并添加摄像头组件
            self.camera_tab = CameraWidget()
            tab_widget.addTab(self.camera_tab, "摄像头")
            self.camera_tab.settings_changed.connect(self._on_settings_changed)

            # 创建并添加音频设备组件
            self.audio_tab = AudioWidget()
            tab_widget.addTab(self.audio_tab, "音频设备")
            self.audio_tab.settings_changed.connect(self._on_settings_changed)

            # 创建并添加快捷键设置组件
            self.shortcuts_tab = ShortcutsSettingsWidget()
            tab_widget.addTab(self.shortcuts_tab, "快捷键")
            self.shortcuts_tab.settings_changed.connect(self._on_settings_changed)

            self.logger.debug("Success添加所有组件选项卡")

        except Exception as e:
            self.logger.error(f"添加组件选项卡Failure: {e}", exc_info=True)

    def _on_settings_changed(self):
        """
        设置变更回调.
        """
        # 可以在此添加一些提示或者其他逻辑

    def _get_ui_controls(self):
        """
        GetUI控件引用.
        """
        # 只需要Get主要的按钮控件
        self.ui_controls.update(
            {
                "save_btn": self.findChild(QPushButton, "save_btn"),
                "cancel_btn": self.findChild(QPushButton, "cancel_btn"),
                "reset_btn": self.findChild(QPushButton, "reset_btn"),
            }
        )

    def _connect_events(self):
        """
        Connect事件处理.
        """
        if self.ui_controls["save_btn"]:
            self.ui_controls["save_btn"].clicked.connect(self._on_save_clicked)

        if self.ui_controls["cancel_btn"]:
            self.ui_controls["cancel_btn"].clicked.connect(self.reject)

        if self.ui_controls["reset_btn"]:
            self.ui_controls["reset_btn"].clicked.connect(self._on_reset_clicked)

    # ConfigurationLoad现在由各个组件自行处理，不需要在主窗口中处理

    # 移除了不再需要的控件操作方法，现在由各个组件处理

    def _on_save_clicked(self):
        """
        Save按钮点击事件.
        """
        try:
            # 收集所有Configuration数据
            success = self._save_all_config()

            if success:
                # 显示SaveSuccess并提示Restart
                reply = QMessageBox.question(
                    self,
                    "ConfigurationSaveSuccess",
                    "Configuration已SaveSuccess！\n\n为了使Configuration生效，建议Restart软件。\n是否现在Restart？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )

                if reply == QMessageBox.Yes:
                    self._restart_application()
                else:
                    self.accept()
            else:
                QMessageBox.warning(self, "Error", "ConfigurationSaveFailure，请检查输入的值。")

        except Exception as e:
            self.logger.error(f"SaveConfigurationFailure: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"SaveConfiguration时发生Error: {str(e)}")

    def _save_all_config(self) -> bool:
        """
        Save所有Configuration.
        """
        try:
            # 从各个组件收集Configuration数据
            all_config_data = {}

            # 系统选项Configuration
            if self.system_options_tab:
                system_config = self.system_options_tab.get_config_data()
                all_config_data.update(system_config)

            # 唤醒词Configuration
            if self.wake_word_tab:
                wake_word_config = self.wake_word_tab.get_config_data()
                all_config_data.update(wake_word_config)
                # Save唤醒词文件
                self.wake_word_tab.save_keywords()

            # 摄像头Configuration
            if self.camera_tab:
                camera_config = self.camera_tab.get_config_data()
                all_config_data.update(camera_config)

            # 音频设备Configuration
            if self.audio_tab:
                audio_config = self.audio_tab.get_config_data()
                all_config_data.update(audio_config)

            # 快捷键Configuration
            if self.shortcuts_tab:
                # 快捷键组件有自己的Save方法
                self.shortcuts_tab.apply_settings()

            # 批量UpdateConfiguration
            for config_path, value in all_config_data.items():
                self.config_manager.update_config(config_path, value)

            self.logger.info("ConfigurationSaveSuccess")
            return True

        except Exception as e:
            self.logger.error(f"SaveConfiguration时出错: {e}", exc_info=True)
            return False

    def _on_reset_clicked(self):
        """
        重置按钮点击事件.
        """
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置所有Configuration为默认值吗？\n这将清除当前的所有设置。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self._reset_to_defaults()

    def _reset_to_defaults(self):
        """
        重置为默认值.
        """
        try:
            # 让各个组件重置为默认值
            if self.system_options_tab:
                self.system_options_tab.reset_to_defaults()

            if self.wake_word_tab:
                self.wake_word_tab.reset_to_defaults()

            if self.camera_tab:
                self.camera_tab.reset_to_defaults()

            if self.audio_tab:
                self.audio_tab.reset_to_defaults()

            if self.shortcuts_tab:
                self.shortcuts_tab.reset_to_defaults()

            self.logger.info("所有组件Configuration已重置为默认值")

        except Exception as e:
            self.logger.error(f"重置ConfigurationFailure: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"重置Configuration时发生Error: {str(e)}")

    def _restart_application(self):
        """
        Restart应用程序.
        """
        try:
            self.logger.info("用户选择Restart应用程序")

            # Close设置窗口
            self.accept()

            # 直接Restart程序
            self._direct_restart()

        except Exception as e:
            self.logger.error(f"Restart应用程序Failure: {e}", exc_info=True)
            QMessageBox.warning(
                self, "RestartFailure", "自动RestartFailure，请手动Restart软件以使Configuration生效。"
            )

    def _direct_restart(self):
        """
        直接Restart程序.
        """
        try:
            import sys

            from PyQt5.QtWidgets import QApplication

            # Get当前执行的程序路径和参数
            python = sys.executable
            script = sys.argv[0]
            args = sys.argv[1:]

            self.logger.info(f"Restart命令: {python} {script} {' '.join(args)}")

            # Close当前应用
            QApplication.quit()

            # Start新实例
            if getattr(sys, "frozen", False):
                # 打包环境
                os.execv(sys.executable, [sys.executable] + args)
            else:
                # 开发环境
                os.execv(python, [python, script] + args)

        except Exception as e:
            self.logger.error(f"直接RestartFailure: {e}", exc_info=True)

    def closeEvent(self, event):
        """
        窗口Close事件.
        """
        self.logger.debug("设置窗口Closed")
        super().closeEvent(event)
