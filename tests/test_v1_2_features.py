import unittest
import numpy as np
from fly_jjs.core.rl import RewardSystem

class TestVersion12Features(unittest.TestCase):
    def test_manual_reward_system(self):
        rs = RewardSystem()
        dummy_img = np.zeros((100, 100, 4), dtype=np.uint8)

        # Test positive manual reward (+)
        reward_pos, events_pos = rs.compute(0.1, 0.0, set(), dummy_img, manual_reward=1.5)
        self.assertIn("MANUAL DOPAMINE TREAT (+1.5)", events_pos)
        self.assertGreaterEqual(reward_pos, 1.4)

        # Test negative manual penalty (-)
        reward_neg, events_neg = rs.compute(0.1, 0.0, set(), dummy_img, manual_reward=-1.5)
        self.assertIn("MANUAL PENALTY (-1.5)", events_neg)
        self.assertLessEqual(reward_neg, -1.4)

if __name__ == '__main__':
    unittest.main()
