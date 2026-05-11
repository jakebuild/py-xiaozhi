import json
import uuid
from typing import Any, Dict

from src.utils.logging_config import get_logger
from src.utils.resource_finder import resource_finder

logger = get_logger(__name__)


class ConfigManager:
    """Configuration管理器 - 单例模式"""

    _instance = None

    # 默认Configuration
    DEFAULT_CONFIG = {
        "SYSTEM_OPTIONS": {
            "CLIENT_ID": None,
            "DEVICE_ID": None,
            "NETWORK": {
                "OTA_VERSION_URL": "https://api.tenclass.net/xiaozhi/ota/",
                "WEBSOCKET_URL": None,
                "WEBSOCKET_ACCESS_TOKEN": None,
                "MQTT_INFO": None,
                "ACTIVATION_VERSION": "v2",  # 可选值: v1, v2
                "AUTHORIZATION_URL": "https://xiaozhi.me/",
            },
        },
        "WAKE_WORD_OPTIONS": {
            "USE_WAKE_WORD": True,
            "MODEL_PATH": "models",
            "NUM_THREADS": 4,
            "PROVIDER": "cpu",
            "MAX_ACTIVE_PATHS": 2,
            "KEYWORDS_SCORE": 1.8,
            "KEYWORDS_THRESHOLD": 0.2,
            "NUM_TRAILING_BLANKS": 1,
        },
        "CAMERA": {
            "camera_index": 0,
            "frame_width": 640,
            "frame_height": 480,
            "fps": 30,
            "Local_VL_url": "https://open.bigmodel.cn/api/paas/v4/",
            "VLapi_key": "",
            "models": "glm-4v-plus",
        },
        "SHORTCUTS": {
            "ENABLED": True,
            "MANUAL_PRESS": {"modifier": "ctrl", "key": "j", "description": "Push-to-talk"},
            "AUTO_TOGGLE": {"modifier": "ctrl", "key": "k", "description": "Auto Conversation"},
            "ABORT": {"modifier": "ctrl", "key": "q", "description": "Abort conversation"},
            "MODE_TOGGLE": {"modifier": "ctrl", "key": "m", "description": "切换模式"},
            "WINDOW_TOGGLE": {
                "modifier": "ctrl",
                "key": "w",
                "description": "显示/隐藏窗口",
            },
        },
        "AEC_OPTIONS": {
            "ENABLED": False,
            "BUFFER_MAX_LENGTH": 200,
            "FRAME_DELAY": 3,
            "FILTER_LENGTH_RATIO": 0.4,
            "ENABLE_PREPROCESS": True,
        },
        "AUDIO_DEVICES": {
            "input_device_id": None,
            "input_device_name": None,
            "output_device_id": None,
            "output_device_name": None,
            "input_sample_rate": None,
            "output_sample_rate": None,
            "input_channels": None,
            "output_channels": None,
        },
    }

    def __new__(cls):
        """
        确保单例模式.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        InitializationConfiguration管理器.
        """
        if self._initialized:
            return
        self._initialized = True

        # InitializationConfiguration文件路径
        self._init_config_paths()

        # 确保必要的目录存在
        self._ensure_required_directories()

        # LoadConfiguration
        self._config = self._load_config()

    def _init_config_paths(self):
        """
        InitializationConfiguration文件路径.
        """
        # 使用resource_finder查找或创建Configuration目录
        self.config_dir = resource_finder.find_config_dir()
        if not self.config_dir:
            # 如果找不到Configuration目录，在项目根目录下创建
            project_root = resource_finder.get_project_root()
            self.config_dir = project_root / "config"
            self.config_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建Configuration目录: {self.config_dir.absolute()}")

        self.config_file = self.config_dir / "config.json"

        # 记录Configuration文件路径
        logger.info(f"Configuration目录: {self.config_dir.absolute()}")
        logger.info(f"Configuration文件: {self.config_file.absolute()}")

    def _ensure_required_directories(self):
        """
        确保必要的目录存在.
        """
        project_root = resource_finder.get_project_root()

        # 创建 models 目录
        models_dir = project_root / "models"
        if not models_dir.exists():
            models_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建模型目录: {models_dir.absolute()}")

        # 创建 cache 目录
        cache_dir = project_root / "cache"
        if not cache_dir.exists():
            cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建缓存目录: {cache_dir.absolute()}")

    def _load_config(self) -> Dict[str, Any]:
        """
        LoadConfiguration文件，如果不存在则创建.
        """
        try:
            # 首先尝试使用resource_finder查找Configuration文件
            config_file_path = resource_finder.find_file("config/config.json")

            if config_file_path:
                logger.debug(f"使用resource_finder找到Configuration文件: {config_file_path}")
                config = json.loads(config_file_path.read_text(encoding="utf-8"))
                return self._merge_configs(self.DEFAULT_CONFIG, config)

            # 如果resource_finder没找到，尝试使用实例变量中的路径
            if self.config_file.exists():
                logger.debug(f"使用实例路径找到Configuration文件: {self.config_file}")
                config = json.loads(self.config_file.read_text(encoding="utf-8"))
                return self._merge_configs(self.DEFAULT_CONFIG, config)
            else:
                # 创建默认Configuration文件
                logger.info("Configuration文件不存在，创建默认Configuration")
                self._save_config(self.DEFAULT_CONFIG)
                return self.DEFAULT_CONFIG.copy()

        except Exception as e:
            logger.error(f"ConfigurationLoadError: {e}")
            return self.DEFAULT_CONFIG.copy()

    def _save_config(self, config: dict) -> bool:
        """
        SaveConfiguration到文件.
        """
        try:
            # 确保Configuration目录存在
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # SaveConfiguration文件
            self.config_file.write_text(
                json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.debug(f"Configuration已Save到: {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"ConfigurationSaveError: {e}")
            return False

    @staticmethod
    def _merge_configs(default: dict, custom: dict) -> dict:
        """
        递归合并Configuration字典.
        """
        result = default.copy()
        for key, value in custom.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = ConfigManager._merge_configs(result[key], value)
            else:
                result[key] = value
        return result

    def get_config(self, path: str, default: Any = None) -> Any:
        """
        通过路径GetConfiguration值
        path: 点分隔的Configuration路径，如 "SYSTEM_OPTIONS.NETWORK.MQTT_INFO"
        """
        try:
            value = self._config
            for key in path.split("."):
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def update_config(self, path: str, value: Any) -> bool:
        """
        Update特定Configuration项
        path: 点分隔的Configuration路径，如 "SYSTEM_OPTIONS.NETWORK.MQTT_INFO"
        """
        try:
            current = self._config
            *parts, last = path.split(".")
            for part in parts:
                current = current.setdefault(part, {})
            current[last] = value
            return self._save_config(self._config)
        except Exception as e:
            logger.error(f"ConfigurationUpdateError {path}: {e}")
            return False

    def reload_config(self) -> bool:
        """
        重新LoadConfiguration文件.
        """
        try:
            self._config = self._load_config()
            logger.info("Configuration文件已重新Load")
            return True
        except Exception as e:
            logger.error(f"Configuration重新LoadFailure: {e}")
            return False

    def generate_uuid(self) -> str:
        """
        生成 UUID v4.
        """
        return str(uuid.uuid4())

    def initialize_client_id(self):
        """
        确Save在客户端ID.
        """
        if not self.get_config("SYSTEM_OPTIONS.CLIENT_ID"):
            client_id = self.generate_uuid()
            success = self.update_config("SYSTEM_OPTIONS.CLIENT_ID", client_id)
            if success:
                logger.info(f"已生成新的客户端ID: {client_id}")
            else:
                logger.error("Save新的客户端IDFailure")

    def initialize_device_id_from_fingerprint(self, device_fingerprint):
        """
        从设备指纹Initialization设备ID.
        """
        if not self.get_config("SYSTEM_OPTIONS.DEVICE_ID"):
            try:
                # 从efuse.jsonGetMAC地址作为DEVICE_ID
                mac_address = device_fingerprint.get_mac_address_from_efuse()
                if mac_address:
                    success = self.update_config(
                        "SYSTEM_OPTIONS.DEVICE_ID", mac_address
                    )
                    if success:
                        logger.info(f"从efuse.jsonGetDEVICE_ID: {mac_address}")
                    else:
                        logger.error("SaveDEVICE_IDFailure")
                else:
                    logger.error("无法从efuse.jsonGetMAC地址")
                    # 备用方案：从设备指纹直接Get
                    fingerprint = device_fingerprint.generate_fingerprint()
                    mac_from_fingerprint = fingerprint.get("mac_address")
                    if mac_from_fingerprint:
                        success = self.update_config(
                            "SYSTEM_OPTIONS.DEVICE_ID", mac_from_fingerprint
                        )
                        if success:
                            logger.info(
                                f"使用指纹中的MAC地址作为DEVICE_ID: "
                                f"{mac_from_fingerprint}"
                            )
                        else:
                            logger.error("Save备用DEVICE_IDFailure")
            except Exception as e:
                logger.error(f"InitializationDEVICE_ID时出错: {e}")

    @classmethod
    def get_instance(cls):
        """
        GetConfiguration管理器实例.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
