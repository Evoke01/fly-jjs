import os
import unittest
import numpy as np
from fly_jjs.core.rl import RewardSystem, FlyLearner, get_pixel_grids, detect_opponent, detect_motion

class TestRLModule(unittest.TestCase):
    def test_reward_system_initialization(self):
        rs = RewardSystem()
        self.assertEqual(rs.total_hits_landed, 0)
        self.assertEqual(rs.total_hits_taken, 0)
        self.assertEqual(rs.total_kills, 0)

    def test_fly_learner_updates(self):
        learner = FlyLearner(num_dns=100, num_actions=14, lr=0.01)
        brain_state = np.zeros(100, dtype=np.uint8)
        brain_state[:10] = 1  # 10 active neurons
        actions_mask = np.zeros(14, dtype=np.float32)
        actions_mask[4] = 1.0 # Melee action

        initial_weights = learner.action_weights.copy()
        learner.update(brain_state, actions_mask, reward=1.0)

        self.assertGreater(learner.updates, 0)
        self.assertGreater(learner.total_reward, 0)
        self.assertFalse(np.array_equal(initial_weights, learner.action_weights))

    def test_vision_processing(self):
        dummy_img = np.zeros((100, 100, 4), dtype=np.uint8)
        dummy_img[:, :, 2] = 255  # Red screen
        r_grid, b_grid, gray = get_pixel_grids(dummy_img)

        self.assertEqual(r_grid.shape, (64,))
        self.assertEqual(b_grid.shape, (64,))
        self.assertGreater(np.sum(r_grid), 0)

        dx_size, threat = detect_opponent(gray, 100, 100)
        self.assertIsInstance(threat, float)

        motion = detect_motion(gray, gray)
        self.assertEqual(motion, 0.0)

if __name__ == '__main__':
    unittest.main()
