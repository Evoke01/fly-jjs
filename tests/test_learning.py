import os
import tempfile
import unittest

import numpy as np

from fly_jjs.core.learning import LEGACY_WEIGHT_SCALE, FlyLearner, sidecar_path

N_DN, N_ACT = 60, 14


def context_features(ctx, rng):
    """Descending-neuron rates: context 0 lights up neurons 0-19, context 1 neurons 20-39."""
    x = rng.random(N_DN).astype(np.float32) * 0.04
    lo = 0 if ctx == 0 else 20
    x[lo:lo + 20] += rng.random(20).astype(np.float32) * 0.5
    return x


class TestFlyLearner(unittest.TestCase):
    def test_learns_the_rewarded_action_in_each_context(self):
        """Melee pays off in context 0 and block in context 1, three frames later;
        meleeing in context 1 gets you hit."""
        rng = np.random.default_rng(1)
        learner = FlyLearner(N_DN, N_ACT, seed=1)
        innate = np.full(N_ACT, -1.5, dtype=np.float32)
        pending, ctx, log = [], 0, []
        for t in range(4000):
            if t % 25 == 0:
                ctx = int(rng.integers(2))
            x = context_features(ctx, rng)
            reward = sum(v for due, v in pending if due == t)
            pending = [p for p in pending if p[0] > t]
            mask, probs = learner.act(x, innate)
            learner.update(x, mask, reward, probs=probs)
            if mask[4 if ctx == 0 else 10]:
                pending.append((t + 3, 1.0))
            if ctx == 1 and mask[4]:
                pending.append((t + 3, -0.5))           # attacking into their attack: you get hit
            if mask.sum():
                pending.append((t + 1, -0.02 * mask.sum()))
            log.append((ctx, probs))
        tail = log[-500:]
        melee_a = np.mean([p[4] for c, p in tail if c == 0])
        block_b = np.mean([p[10] for c, p in tail if c == 1])
        melee_b = np.mean([p[4] for c, p in tail if c == 1])
        others = np.mean([np.delete(p, [4, 10]).mean() for _, p in tail])
        self.assertGreater(melee_a, 0.85)
        self.assertGreater(block_b, 0.85)
        self.assertGreater(melee_a - melee_b, 0.2)     # it learned *when*, not just *what*
        self.assertLess(others, 0.3)                    # and it does not mash every key

    def test_dopamine_is_a_reward_prediction_error(self):
        """A reward the fly has learned to expect stops causing dopamine; a surprise does."""
        learner = FlyLearner(N_DN, N_ACT, seed=0)
        x = np.zeros(N_DN, dtype=np.float32)
        x[:10] = 0.5
        none = np.zeros(N_ACT, dtype=np.float32)
        first = None
        for t in range(3000):
            d = learner.update(x, none, reward=0.5)
            if t == 1:
                first = d
        self.assertGreater(first, 0.3)
        self.assertLess(abs(learner.dopamine), 0.05)
        self.assertGreater(learner.update(x, none, reward=2.5), 1.0)       # better than expected
        learner.update(x, none, reward=0.5)
        self.assertLess(learner.update(x, none, reward=-1.0), -1.0)        # worse than expected

    def test_imitation_learns_the_players_keys(self):
        rng = np.random.default_rng(2)
        learner = FlyLearner(N_DN, N_ACT, seed=2)
        for t in range(3000):
            ctx = int(rng.integers(2))
            target = np.zeros(N_ACT, dtype=np.float32)
            target[0 if ctx == 0 else 10] = 1.0          # forward in context 0, block in 1
            learner.imitate(context_features(ctx, rng), target, reward=0.0)
        p0 = learner.policy(context_features(0, rng))
        p1 = learner.policy(context_features(1, rng))
        self.assertGreater(p0[0], 0.7)
        self.assertLess(p0[10], 0.3)
        self.assertGreater(p1[10], 0.7)
        self.assertLess(p1[0], 0.3)
        self.assertLess(np.delete(p0, [0, 10]).max(), 0.2)
        self.assertEqual(learner.imitation_updates, 3000)

    def test_policy_always_keeps_exploring(self):
        learner = FlyLearner(N_DN, N_ACT)
        learner.action_weights[:] = 50.0
        learner.action_bias[:] = -50.0
        p = learner.policy(np.ones(N_DN, dtype=np.float32))
        self.assertTrue(np.all(p < 1.0) and np.all(p > 0.0))
        self.assertTrue(np.all(p > 0.01))

    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "fly_weights.npy")
            a = FlyLearner(N_DN, N_ACT, seed=3)
            a.action_weights = np.random.default_rng(3).normal(size=(N_DN, N_ACT)).astype(np.float32)
            a.action_bias[:] = 0.25
            a.value_weights[:] = 0.5
            a.value_bias = -1.0
            a.save(path)
            self.assertTrue(os.path.exists(sidecar_path(path)))
            self.assertEqual(np.load(path).shape, (N_DN, N_ACT))   # same file format as before

            b = FlyLearner(N_DN, N_ACT)
            self.assertTrue(b.load(path))
            np.testing.assert_allclose(b.action_weights, a.action_weights)
            np.testing.assert_allclose(b.action_bias, a.action_bias)
            np.testing.assert_allclose(b.value_weights, a.value_weights)
            self.assertAlmostEqual(b.value_bias, -1.0, places=5)

    def test_old_weights_are_converted_not_saturated(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "fly_weights.npy")
            old = np.zeros((N_DN, N_ACT), dtype=np.float32)
            old[:, 0] = 2.0                               # a Hebbian matrix from the old trainer
            old[:, 3] = 1.0
            np.save(path, old)
            learner = FlyLearner(N_DN, N_ACT)
            self.assertTrue(learner.load(path))
            self.assertAlmostEqual(float(np.abs(learner.action_weights).max()), LEGACY_WEIGHT_SCALE, places=6)
            p = learner.policy(np.full(N_DN, 0.05, dtype=np.float32))
            self.assertGreater(p[0], p[3])                # old preferences survive...
            self.assertLess(p[0], 0.9)                    # ...without pinning the key down

    def test_load_resizes_to_the_connectome(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "fly_weights.npy")
            np.save(path, np.ones((10, 14), dtype=np.float32))
            learner = FlyLearner(N_DN, N_ACT)
            self.assertTrue(learner.load(path))
            self.assertEqual(learner.action_weights.shape, (N_DN, N_ACT))

    def test_missing_file_starts_from_scratch(self):
        learner = FlyLearner(N_DN, N_ACT)
        self.assertFalse(learner.load(os.path.join(tempfile.gettempdir(), "does_not_exist_fly.npy")))
        self.assertFalse(np.any(learner.action_weights))


if __name__ == "__main__":
    unittest.main()
