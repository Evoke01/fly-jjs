"""End-to-end check against the real connectome.

Skipped unless the flybrain data files are already downloaded (FLY_DATA or ~/fly-data),
so the test suite never triggers the ~260 MB download on its own.
"""
import unittest

import numpy as np

try:
    import flybrain
    HAVE_BRAIN = flybrain.has_data()
except Exception:
    HAVE_BRAIN = False


def scene(t, w=320, h=240):
    """A bright 'opponent' drifting left to right over a darker arena."""
    img = np.full((h, w, 4), 70, dtype=np.uint8)
    img[: int(h * 0.4), :, :3] = (150, 120, 90)
    x = int((t * 7) % (w - 40))
    img[110:170, x:x + 25, :3] = 235
    img[:, :, 3] = 255
    return img


@unittest.skipUnless(HAVE_BRAIN, "flybrain connectome data not downloaded")
class TestConnectomeIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fly_jjs.core.rl import get_brain_components
        cls.components = get_brain_components()

    def test_brain_components(self):
        c = self.components
        self.assertGreater(len(c.dns), 1000)
        self.assertGreater(len(c.reward_dans), 100)     # PAM cluster
        self.assertGreater(len(c.punish_dans), 5)       # PPL1 cluster
        self.assertFalse(np.intersect1d(c.reward_dans, c.dns).size)   # dopamine is not a motor neuron

    def test_eyes_use_real_visual_neurons_at_every_resolution(self):
        from fly_jjs.core.config import RESOLUTION_PRESETS
        from fly_jjs.core.vision import FlyEyes
        brain = self.components.brain
        visual = set(np.flatnonzero(np.char.find(brain.superclass.astype(str), "visual_projection") >= 0))
        for res in RESOLUTION_PRESETS:
            eyes = FlyEyes(brain, res, use_color=True)
            self.assertGreater(eyes.num_neurons, 1500, res)
            eyes.inject(scene(0))
            injected = np.concatenate([np.atleast_1d(i) for i, _ in eyes.inject(scene(1))])
            self.assertTrue(set(injected.tolist()) <= visual, res)

    def test_play_loop_steps(self):
        from fly_jjs.core.learning import FlyLearner
        from fly_jjs.core.rl import NUM_ACTIONS, FlyBody
        from fly_jjs.core.vision import FlyEyes, detect_opponent
        c = self.components
        body = FlyBody(c, FlyEyes(c.brain, "64x48", use_color=True))
        learner = FlyLearner(len(c.dns), NUM_ACTIONS, seed=0)
        pressed = 0
        for t in range(40):
            img = scene(t)
            gray = img[:, :, :3].mean(axis=2).astype(np.uint8)
            opp, threat = detect_opponent(gray, img.shape[1], img.shape[0])
            rates = body.step(img, opp, threat, learner.dopamine)
            innate, pop_rates = body.innate_drive(rates)
            mask, probs = learner.act(rates, innate)
            learner.update(rates, mask, reward=0.1, probs=probs)
            pressed += mask.sum()
        self.assertEqual(rates.shape, (len(c.dns),))
        self.assertTrue(np.all((rates >= 0) & (rates <= 1)))
        self.assertTrue(np.all(np.isfinite(innate)))
        self.assertGreater(body.fired, 0)
        self.assertGreater(pressed, 0)                   # the untrained fly does act
        self.assertLess(pressed, 40 * NUM_ACTIONS * 0.6)  # ...without mashing every key


if __name__ == "__main__":
    unittest.main()
