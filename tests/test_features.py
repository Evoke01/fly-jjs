import unittest
import numpy as np
from fly_jjs.core.storage import WEIGHTS_PATH
from fly_jjs.core.profiles import ProfileManager
from fly_jjs.core.analytics import BrainAnalytics
from fly_jjs.core.music_experiment import NeuralHealthTracker

class TestNewFeatures(unittest.TestCase):
    def setUp(self):
        # WEIGHTS_PATH lives in the throwaway FLY_JJS_HOME set up by tests/__init__.py.
        self.wpath = WEIGHTS_PATH
        np.save(self.wpath, np.ones((50, 14), dtype=np.float32))

    def test_profile_manager(self):
        ok, msg = ProfileManager.save_profile("unit_test_profile", "Test Profile Desc")
        self.assertTrue(ok)

        profiles = ProfileManager.list_profiles()
        names = [p["name"] for p in profiles]
        self.assertIn("unit_test_profile", names)

        ok, msg = ProfileManager.load_profile("unit_test_profile")
        self.assertTrue(ok)

        ok, msg = ProfileManager.delete_profile("unit_test_profile")
        self.assertTrue(ok)

    def test_brain_analytics(self):
        data = BrainAnalytics.analyze()
        self.assertTrue(data["exists"])
        self.assertIn("top_action", data)
        self.assertIn("biases", data)

    def test_neural_health_tracker(self):
        tracker = NeuralHealthTracker(num_neurons=50)
        brain_state = np.ones(50, dtype=np.uint8)
        health = tracker.update(brain_state, arousal=0.5, dopamine=0.2, fired_count=25)

        self.assertIn("phase", health)
        self.assertIn("stress_level", health)
        self.assertIn("meme", health)

if __name__ == '__main__':
    unittest.main()
