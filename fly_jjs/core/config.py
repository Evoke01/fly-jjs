import os
import json

USER_DIR = os.path.expanduser("~/.fly_jjs")
os.makedirs(USER_DIR, exist_ok=True)
CONFIG_PATH = os.path.join(USER_DIR, "config.json")

DEFAULT_CONFIG = {
    "resolution": "8x8",          # "8x8", "16x16", "32x32", "192x144", "320x240"
    "use_color": True,            # True (Full RGB) or False (Grayscale)
    "device_tier": "mid",         # "low" (4GB RAM), "mid" (8GB RAM), "high" (16GB RAM)
    "camera_lock_enabled": True,  # Enable smooth mouse target locking
    "camera_sensitivity": 0.3,    # Mouse smooth movement factor
    "pattern_recognition": True,  # Enable temporal movement pattern tracking
}

RESOLUTION_PRESETS = {
    "8x8": (8, 8),
    "16x16": (16, 16),
    "32x32": (32, 32),
    "192x144": (192, 144),
    "320x240": (320, 240),
}

DEVICE_TIERS = {
    "low": {
        "name": "Low-End Mode",
        "min_ram": "4 GB RAM",
        "fps_target": 20,
        "default_res": "8x8",
        "default_color": False,
        "description": "Optimized for low-spec PCs. Fast execution, low memory overhead."
    },
    "mid": {
        "name": "Mid-End Mode",
        "min_ram": "8 GB RAM",
        "fps_target": 30,
        "default_res": "192x144",
        "default_color": True,
        "description": "Balanced performance and visual detail."
    },
    "high": {
        "name": "High-End Mode",
        "min_ram": "16 GB RAM",
        "fps_target": 60,
        "default_res": "320x240",
        "default_color": True,
        "description": "Full resolution RGB picture processing with 60 FPS target."
    }
}

class ConfigManager:
    @staticmethod
    def load_config():
        if not os.path.exists(CONFIG_PATH):
            ConfigManager.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
        try:
            with open(CONFIG_PATH, "r") as f:
                cfg = json.load(f)
            # Merge missing default keys
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
        except Exception:
            return DEFAULT_CONFIG.copy()

    @staticmethod
    def save_config(cfg):
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(cfg, f, indent=2)
            return True
        except Exception as e:
            print(f"[Config] Error saving config: {e}")
            return False

    @staticmethod
    def set_device_tier(tier):
        if tier in DEVICE_TIERS:
            cfg = ConfigManager.load_config()
            cfg["device_tier"] = tier
            cfg["resolution"] = DEVICE_TIERS[tier]["default_res"]
            cfg["use_color"] = DEVICE_TIERS[tier]["default_color"]
            ConfigManager.save_config(cfg)
            return True
        return False
