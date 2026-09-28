import importlib.util
import json
import os
import tempfile
import time
import unittest

import numpy as np

from fly_jjs.core import storage
from fly_jjs.core.config import CONFIG_VERSION, DEFAULT_CONFIG, ConfigManager
from fly_jjs.core.profiles import ProfileManager
from fly_jjs.core.rl import ManualRewards
from fly_jjs.core.telemetry import TelemetryPublisher, read_snapshot, render


class TestTelemetry(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "telemetry.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_publish_and_read(self):
        pub = TelemetryPublisher("play", interval=0.0, path=self.path)
        self.assertTrue(pub.publish({"step": 7, "dopamine": 0.5, "actions": {"melee": 0.9}}))
        snap = read_snapshot(self.path)
        self.assertEqual(snap["mode"], "play")
        self.assertEqual(snap["step"], 7)
        self.assertFalse(snap["stale"])

    def test_publish_is_rate_limited(self):
        pub = TelemetryPublisher("play", interval=60.0, path=self.path)
        self.assertTrue(pub.publish({"step": 1}))
        self.assertFalse(pub.publish({"step": 2}))
        self.assertEqual(read_snapshot(self.path)["step"], 1)

    def test_ended_and_old_sessions_are_stale(self):
        pub = TelemetryPublisher("train", interval=0.0, path=self.path)
        pub.publish({"step": 1})
        pub.close()
        self.assertTrue(read_snapshot(self.path)["stale"])

        with open(self.path, "w") as f:
            json.dump({"step": 3, "time": time.time() - 60}, f)
        self.assertTrue(read_snapshot(self.path)["stale"])

    def test_missing_or_broken_file(self):
        self.assertIsNone(read_snapshot(self.path))
        with open(self.path, "w") as f:
            f.write("{not json")
        self.assertIsNone(read_snapshot(self.path))

    def test_render_does_not_crash(self):
        if importlib.util.find_spec("rich") is None:
            self.skipTest("rich not installed")
        from rich.console import Console
        console = Console(file=open(os.devnull, "w"), width=140)
        console.print(render(None))
        pub = TelemetryPublisher("manual", interval=0.0, path=self.path)
        pub.publish({"step": 5, "actions": {"melee": 0.7, "block": 0.1}, "pressed": ["melee"],
                     "innate": {"melee": 0.2}, "vision": {"on": 0.3, "motion": 0.1},
                     "opponent": {"dx": -40, "size": 30, "threat": 0.4}, "pattern_burst": True,
                     "hits": {"landed": 2, "taken": 1, "kills": 0}, "events": ["HIT ENEMY (+2.0)"]})
        console.print(render(read_snapshot(self.path)))


class TestStorageAndProfiles(unittest.TestCase):
    def setUp(self):
        np.save(storage.WEIGHTS_PATH, np.full((20, 14), 0.5, dtype=np.float32))
        np.savez(storage.LEARNER_PATH, action_bias=np.ones(14, dtype=np.float32))

    def tearDown(self):
        storage.wipe_memory()
        for name in ("unit_sidecar", "old_profile"):
            ProfileManager.delete_profile(name)

    def test_backup_includes_the_critic(self):
        path = storage.create_backup_of_weights()
        self.assertTrue(os.path.exists(path))
        self.assertTrue(os.path.exists(path[:-len(".npy")] + "_learner.npz"))

    def test_profiles_carry_the_whole_learner(self):
        ok, _ = ProfileManager.save_profile("unit_sidecar", "with critic")
        self.assertTrue(ok)
        storage.wipe_memory()
        self.assertFalse(os.path.exists(storage.LEARNER_PATH))
        ok, _ = ProfileManager.load_profile("unit_sidecar")
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(storage.WEIGHTS_PATH))
        self.assertTrue(os.path.exists(storage.LEARNER_PATH))

    def test_loading_an_old_profile_drops_the_stale_critic(self):
        pdir = os.path.join(storage.PROFILES_DIR, "old_profile")
        os.makedirs(pdir, exist_ok=True)
        np.save(os.path.join(pdir, "fly_weights.npy"), np.zeros((20, 14), dtype=np.float32))
        ok, _ = ProfileManager.load_profile("old_profile")
        self.assertTrue(ok)
        self.assertFalse(os.path.exists(storage.LEARNER_PATH))

    def test_profile_names_cannot_escape_the_profiles_folder(self):
        for name in ("..", "../..", "", "/"):
            ok, _ = ProfileManager.delete_profile(name)
            self.assertFalse(ok)
        self.assertTrue(os.path.isdir(storage.USER_DIR))
        self.assertTrue(os.path.exists(storage.WEIGHTS_PATH))

    def test_wipe_memory_removes_both_files(self):
        self.assertTrue(storage.wipe_memory())
        self.assertFalse(os.path.exists(storage.WEIGHTS_PATH))
        self.assertFalse(os.path.exists(storage.LEARNER_PATH))
        self.assertFalse(storage.wipe_memory())


class TestConfigMigration(unittest.TestCase):
    def tearDown(self):
        ConfigManager.save_config(dict(DEFAULT_CONFIG))

    def _write(self, cfg):
        with open(storage.CONFIG_PATH, "w") as f:
            json.dump(cfg, f)

    def test_untouched_old_default_moves_past_8x8(self):
        self._write({"resolution": "8x8", "device_tier": "mid", "use_color": True})
        cfg = ConfigManager.load_config()
        self.assertEqual(cfg["resolution"], DEFAULT_CONFIG["resolution"])
        self.assertEqual(cfg["config_version"], CONFIG_VERSION)

    def test_deliberate_low_end_choice_is_kept(self):
        self._write({"resolution": "8x8", "device_tier": "low", "use_color": False})
        self.assertEqual(ConfigManager.load_config()["resolution"], "8x8")

    def test_unknown_values_fall_back_to_defaults(self):
        self._write({"config_version": CONFIG_VERSION, "resolution": "4000x3000", "device_tier": "ultra"})
        cfg = ConfigManager.load_config()
        self.assertEqual(cfg["resolution"], DEFAULT_CONFIG["resolution"])
        self.assertEqual(cfg["device_tier"], DEFAULT_CONFIG["device_tier"])


class TestManualRewards(unittest.TestCase):
    def test_treats_and_penalties_accumulate_until_taken(self):
        manual = ManualRewards(listen=False)
        manual.give(+1.5)
        manual.give(+1.5)
        self.assertAlmostEqual(manual.take(), 3.0)
        self.assertEqual(manual.take(), 0.0)
        manual.give(-1.5)
        self.assertAlmostEqual(manual.take(), -1.5)

    def test_mashing_is_capped(self):
        manual = ManualRewards(listen=False)
        for _ in range(10):
            manual.give(+1.5)
        self.assertAlmostEqual(manual.take(), 3.0)


if __name__ == "__main__":
    unittest.main()
