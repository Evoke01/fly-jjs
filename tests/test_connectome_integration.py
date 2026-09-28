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
        self.assertGreater(len(c.readout), 50000)
        np.testing.assert_array_equal(c.readout[:len(c.dns)], c.dns)   # old weight files map onto DNs
        self.assertEqual(len(np.unique(c.readout)), len(c.readout))
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
        from fly_jjs.core.combat import REST_LOGIT
        from fly_jjs.core.learning import FlyLearner
        from fly_jjs.core.rl import NUM_ACTIONS, FlyBody
        from fly_jjs.core.vision import FlyEyes, detect_opponent
        c = self.components
        body = FlyBody(c, FlyEyes(c.brain, "64x48", use_color=True))
        learner = FlyLearner(body.num_inputs, NUM_ACTIONS, seed=0)
        pressed = 0
        for t in range(40):
            img = scene(t)
            gray = img[:, :, :3].mean(axis=2).astype(np.uint8)
            opp, threat = detect_opponent(gray, img.shape[1], img.shape[0])
            rates = body.step(img, opp, threat, learner.dopamine)
            drive, pop_rates = body.innate_drive(rates)
            innate = REST_LOGIT + drive
            mask, probs = learner.act(rates, innate)
            learner.update(rates, mask, reward=0.1, probs=probs)
            pressed += mask.sum()
        self.assertEqual(rates.shape, (body.num_inputs,))
        self.assertGreater(body.num_inputs, 50000)       # the fly reads far more than its 1.3k DNs
        self.assertTrue(np.all((rates >= 0) & (rates <= 1)))
        self.assertTrue(np.all(np.isfinite(innate)))
        self.assertGreater(body.fired, 0)
        self.assertGreater(pressed, 0)                   # the untrained fly does act
        self.assertLess(pressed, 40 * NUM_ACTIONS * 0.6)  # ...without mashing every key

    def test_resting_motor_populations_do_not_bias_the_fly(self):
        """Regression: the motor populations are arbitrary slices of the descending neurons.
        Read against fixed thresholds, their resting rates set the odds of the moves anywhere
        from -0.1 to -3.5, whatever happened in the fight."""
        from fly_jjs.core.rl import FlyBody
        from fly_jjs.core.vision import FlyEyes, detect_opponent
        c = self.components
        body = FlyBody(c, FlyEyes(c.brain, "64x48", use_color=True))
        drives = []
        for t in range(120):
            img = scene(t)
            gray = img[:, :, :3].mean(axis=2).astype(np.uint8)
            opp, threat = detect_opponent(gray, img.shape[1], img.shape[0])
            drives.append(body.innate_drive(body.step(img, opp, threat))[0])
        settled = np.array(drives[60:])
        self.assertLess(np.abs(settled.mean(axis=0)).max(), 1.5)    # no move favoured at rest
        self.assertGreater(settled.std(axis=0).mean(), 0.01)       # but the brain still has a say

    def test_casino_fear_and_3d_view_on_the_real_brain(self):
        from fly_jjs.core.casino import Casino, board_image
        from fly_jjs.core.dashboard import BrainDashboard
        c = self.components
        dash = BrainDashboard(c.brain)
        self.assertEqual(len(dash.layout["positions"]), c.brain.n)
        self.assertTrue(np.all(np.isfinite(dash.layout["positions"])))   # sensory neurons placed too
        casino = Casino(c, {"fear": 1.0}, bot="pro", mode="fast", seed=0, dashboard=dash, verbose=False)
        casino.play_game()
        self.assertGreater(casino.rounds, 0)
        self.assertGreater(dash.state()["stats"]["spikes_per_s"], 0)
        # Full danger drives the real fear circuit, and the connectome carries it on to the
        # giant fibre, the escape neuron.
        fear = casino.fly.fear
        fear.assess(0, 20, rnd=3, stake=2, dread=1.0)
        for _ in range(15):
            casino.fly.step(board_image())
        self.assertGreater(fear.terror, 0.5)
        self.assertGreater(fear.escape_rate, 0.1)
        fear.danger = 0.0
        for _ in range(30):
            casino.fly.step(board_image())
        self.assertLess(fear.terror, 0.2)                                 # and calms down again

    def test_agent_fights_in_the_arena(self):
        from fly_jjs.core.agent import FlyAgent
        from fly_jjs.core.arena import Arena, ArenaInput
        from fly_jjs.core.config import DEFAULT_CONFIG
        c = self.components
        arena = Arena(seed=2, max_seconds=3.0)
        backend = ArenaInput()
        agent = FlyAgent(c, dict(DEFAULT_CONFIG), arena.width, arena.height, backend, seed=2)
        self.assertEqual(agent.learner.num_inputs, len(c.readout))
        agent.new_fight()
        pressed = set()
        while not arena.done:
            step = agent.step(arena.render(), arena.time)
            pressed |= step.actions
            arena.step(backend)
        agent.end_fight(arena.render())
        self.assertTrue(pressed)
        self.assertGreater(agent.learner.updates, 10)
        self.assertEqual(backend.held, set())            # nothing left held down after the fight
        self.assertTrue(np.all(np.isfinite(agent.learner.action_weights)))


if __name__ == "__main__":
    unittest.main()
