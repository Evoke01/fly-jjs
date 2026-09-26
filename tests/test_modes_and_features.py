import os
import unittest
import numpy as np
from fly_jjs.core.config import ConfigManager, DEVICE_TIERS, RESOLUTION_PRESETS
from fly_jjs.core.rl import PatternRecognizer, get_pixel_grids, detect_opponent

class TestModesAndFeatures(unittest.TestCase):
    def test_config_manager(self):
        cfg = ConfigManager.load_config()
        self.assertIn("resolution", cfg)
        self.assertIn("use_color", cfg)
        self.assertIn("device_tier", cfg)

        ok = ConfigManager.set_device_tier("low")
        self.assertTrue(ok)
        cfg_low = ConfigManager.load_config()
        self.assertEqual(cfg_low["device_tier"], "low")
        self.assertEqual(cfg_low["resolution"], "8x8")
        self.assertFalse(cfg_low["use_color"])

        # Reset to mid
        ConfigManager.set_device_tier("mid")

    def test_pattern_recognizer(self):
        pr = PatternRecognizer(history_len=5)
        pr.update(0, 0.1, 0.0)
        pr.update(10, 0.2, 0.1)
        pr.update(20, 0.5, 0.35)
        pr.update(30, 0.7, 0.40)

        burst, avg_m = pr.predict_burst()
        self.assertTrue(burst)
        self.assertGreater(avg_m, 0.1)

    def test_pixel_grids_resolutions(self):
        dummy_img = np.zeros((100, 100, 4), dtype=np.uint8)
        dummy_img[:, :, 2] = 255  # Red screen

        r8, b8, gray = get_pixel_grids(dummy_img, resolution_preset="8x8", use_color=True)
        self.assertEqual(r8.shape, (64,))

        r192, b192, gray = get_pixel_grids(dummy_img, resolution_preset="192x144", use_color=True)
        self.assertEqual(r192.shape, (192 * 144,))

    def test_detect_opponent_3d_position(self):
        gray = np.zeros((200, 200), dtype=np.uint8)
        gray[80:120, 80:120] = 255
        opp, threat = detect_opponent(gray, 200, 200)

        self.assertEqual(len(opp), 3)  # (dx, dy, size)
        self.assertGreater(threat, 0.1)

if __name__ == '__main__':
    unittest.main()
