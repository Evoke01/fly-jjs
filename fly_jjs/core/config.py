import os
import json

from fly_jjs.core.storage import CONFIG_PATH

CONFIG_VERSION = 2

DEFAULT_CONFIG = {
    "config_version": CONFIG_VERSION,
    "resolution": "64x48",        # processing grid, see RESOLUTION_PRESETS
    "use_color": True,            # True (Full RGB) or False (Grayscale)
    "device_tier": "mid",         # "low" (4GB RAM), "mid" (8GB RAM), "high" (16GB RAM)
    "camera_lock_enabled": True,  # Enable smooth mouse target locking
    "camera_sensitivity": 0.3,    # Mouse smooth movement factor
    "pattern_recognition": True,  # Enable temporal movement pattern tracking
    "brain_steps": 2,             # 20 ms brain steps simulated per game frame (1-3)
    "readout": "full",            # "full": ~59k neurons downstream of the eyes; "descending": 1.3k
    "instincts": 1.0,             # strength of innate combat reflexes (0 = brain and learning only)
    "camera_mode": "shiftlock",   # "shiftlock": move the mouse; "hold_right": hold right button to turn
    "opponent_near_height": 0.20, # opponent height / window height at melee range
    "opponent_far_height": 0.06,  # ...and far away (sets the fly's sense of distance)
    "dashboard": False,           # open the 3D brain view in the browser during Play mode
    "dashboard_port": 8765,       # local port of the 3D brain view (127.0.0.1 only)
    "fear": 1.0,                  # casino: 0 = fearless, 1 = normal, 2 = terrified
    "casino_bot": "rookie",       # casino opponent: "random", "rookie", "pro" (or "none")
}

# The frame is shrunk to this grid before the fly's eyes compute contrast, colour and
# motion; the result is then pooled onto the fly's visual neurons (see vision.py).
RESOLUTION_PRESETS = {
    "8x8": (8, 8),
    "16x16": (16, 16),
    "32x32": (32, 32),
    "64x48": (64, 48),
    "128x96": (128, 96),
    "192x144": (192, 144),
    "320x240": (320, 240),
}

DEVICE_TIERS = {
    "low": {
        "name": "Low-End Mode",
        "min_ram": "4 GB RAM",
        "fps_target": 20,
        "default_res": "32x32",
        "default_color": False,
        "brain_steps": 1,
        "description": "Optimized for low-spec PCs. Fast execution, low memory overhead."
    },
    "mid": {
        "name": "Mid-End Mode",
        "min_ram": "8 GB RAM",
        "fps_target": 30,
        "default_res": "64x48",
        "default_color": True,
        "brain_steps": 2,
        "description": "Balanced performance and visual detail."
    },
    "high": {
        "name": "High-End Mode",
        "min_ram": "16 GB RAM",
        "fps_target": 60,
        "default_res": "128x96",
        "default_color": True,
        "brain_steps": 3,
        "description": "Sharpest motion and colour detection with 60 FPS target."
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
            if cfg.get("config_version", 1) < CONFIG_VERSION:
                # Older releases wrote "mid" tier + 8x8 as the untouched default; the fly's
                # eyes now use far more than 64 inputs, so move those to the new default.
                if cfg.get("device_tier", "mid") == "mid" and cfg.get("resolution") == "8x8":
                    cfg["resolution"] = DEFAULT_CONFIG["resolution"]
                tier = cfg.get("device_tier") if cfg.get("device_tier") in DEVICE_TIERS else "mid"
                cfg.setdefault("brain_steps", DEVICE_TIERS[tier]["brain_steps"])
                cfg["config_version"] = CONFIG_VERSION
                ConfigManager.save_config(cfg)
            # Merge missing default keys
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            if cfg.get("resolution") not in RESOLUTION_PRESETS:
                cfg["resolution"] = DEFAULT_CONFIG["resolution"]
            if cfg.get("device_tier") not in DEVICE_TIERS:
                cfg["device_tier"] = DEFAULT_CONFIG["device_tier"]
            if cfg.get("brain_steps") not in (1, 2, 3):
                cfg["brain_steps"] = DEVICE_TIERS[cfg["device_tier"]]["brain_steps"]
            if cfg.get("readout") not in ("full", "descending"):
                cfg["readout"] = DEFAULT_CONFIG["readout"]
            if not isinstance(cfg.get("instincts"), (int, float)):
                cfg["instincts"] = DEFAULT_CONFIG["instincts"]
            if not isinstance(cfg.get("dashboard"), bool):
                cfg["dashboard"] = DEFAULT_CONFIG["dashboard"]
            if not isinstance(cfg.get("dashboard_port"), int) or not 1024 <= cfg["dashboard_port"] <= 65535:
                cfg["dashboard_port"] = DEFAULT_CONFIG["dashboard_port"]
            if not isinstance(cfg.get("fear"), (int, float)) or not 0 <= cfg["fear"] <= 3:
                cfg["fear"] = DEFAULT_CONFIG["fear"]
            if cfg.get("casino_bot") not in ("random", "rookie", "pro", "none"):
                cfg["casino_bot"] = DEFAULT_CONFIG["casino_bot"]
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
            cfg["brain_steps"] = DEVICE_TIERS[tier]["brain_steps"]
            ConfigManager.save_config(cfg)
            return True
        return False
