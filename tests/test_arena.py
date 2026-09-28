import unittest

import numpy as np

from fly_jjs.core.arena import M1, Arena, ArenaInput, _angle_to
from fly_jjs.core.calibrate import calibration_from_boxes
from fly_jjs.core.combat import DEFAULT_HP_BARS, REST_LOGIT, Instincts, RewardSystem, bar_fill, persistence_logits
from fly_jjs.core.actions import ACTION_NAMES, NUM_ACTIONS
from fly_jjs.core.controls import CameraController, InputController
from fly_jjs.core.learning import FlyLearner
from fly_jjs.core.tracking import OpponentTracker


def face_opponent(arena, distance):
    """Put the player `distance` metres in front of a calm opponent, facing it."""
    arena.opp["pos"] = np.array([0.0, 0.0])
    arena.player["pos"] = np.array([0.0, -distance])
    arena.player["yaw"] = _angle_to(arena.player["pos"], arena.opp["pos"])
    arena.opp["state"], arena.opp["t"] = "recover", 0.0


class TestArenaMechanics(unittest.TestCase):
    def test_m1_lands_in_reach_and_misses_out_of_reach(self):
        arena = Arena(seed=0)
        face_opponent(arena, 1.5)
        inp = ArenaInput()
        inp.click()
        arena.step(inp)
        self.assertLess(arena.opp["hp"], 100)
        hp = arena.opp["hp"]
        face_opponent(arena, M1["range"] + 3)
        arena.time += 1.0
        inp.click()
        arena.step(inp)
        self.assertEqual(arena.opp["hp"], hp)

    def test_blocking_softens_hits(self):
        hurt = []
        for block in (False, True):
            arena = Arena(seed=0)
            face_opponent(arena, 1.5)
            arena.player["block"] = block
            arena._hurt_player(10.0)
            hurt.append(100 - arena.player["hp"])
        self.assertLess(hurt[1], hurt[0] / 3)

    def test_dash_moves_and_grants_invulnerability(self):
        arena = Arena(seed=0)
        face_opponent(arena, 6.0)
        start = arena.player["pos"].copy()
        inp = ArenaInput()
        inp.tap("q")
        arena.step(inp)
        self.assertGreater(arena.player["iframes"], 0)
        for _ in range(4):
            arena.step(inp)
        self.assertGreater(np.linalg.norm(arena.player["pos"] - start), 3.0)

    def test_mouse_turns_the_camera(self):
        arena = Arena(seed=0)
        yaw = arena.player["yaw"]
        inp = ArenaInput()
        inp.move(100, 0)
        arena.step(inp)
        self.assertNotAlmostEqual(arena.player["yaw"], yaw)

    def test_render_and_hud_match_the_reward_system(self):
        arena = Arena(seed=0)
        arena.player["hp"], arena.opp["hp"] = 60.0, 30.0
        img = arena.render()
        self.assertEqual(img.shape, (arena.height, arena.width, 4))
        self.assertAlmostEqual(bar_fill(img, DEFAULT_HP_BARS["self"]["roi"], None, "self"), 0.6, delta=0.05)
        self.assertAlmostEqual(bar_fill(img, DEFAULT_HP_BARS["enemy"]["roi"], None, "enemy"), 0.3, delta=0.05)

    def test_hud_stays_readable_during_a_hit_flash(self):
        arena = Arena(seed=0)
        arena.player["hp"], arena.player["hit_flash"] = 80.0, 0.15
        img = arena.render()
        self.assertAlmostEqual(bar_fill(img, DEFAULT_HP_BARS["self"]["roi"], None, "self"), 0.8, delta=0.05)

    def test_knockout_on_the_last_frame_is_rewarded(self):
        arena = Arena(seed=0)
        rewards = RewardSystem()
        for _ in range(3):
            rewards.compute(0.5, 0.0, {"melee"}, arena.render())
        arena.opp["hp"] = 0.0
        reward, events = rewards.compute(0.5, 0.0, {"melee"}, arena.render(), final=True)
        self.assertTrue(any("KILLED OPPONENT" in e for e in events))
        self.assertGreater(reward, 5.0)

    def test_fight_ends_with_a_result(self):
        arena = Arena(seed=0, max_seconds=5.0)
        inp = ArenaInput()
        while not arena.done:
            arena.step(inp)
        self.assertIsNotNone(arena.won)
        self.assertLessEqual(arena.time, 5.0 + 1e-6)


class TestArenaWithoutBrain(unittest.TestCase):
    """The real pipeline minus the connectome: tracker, instincts, controls, rewards."""

    def fight(self, instincts, seed):
        arena = Arena(seed=seed, difficulty=1.0, max_seconds=40.0)
        inp = ArenaInput()
        ctl, cam = InputController(inp), CameraController(inp, arena.width, arena.height)
        rewards = RewardSystem()
        tracker = OpponentTracker(arena.width, arena.height, ignore=[b["roi"] for b in rewards.bars.values()])
        instinct = Instincts(instincts, seed=seed)
        rng = np.random.default_rng(seed)
        prev = np.zeros(NUM_ACTIONS, dtype=np.float32)
        while not arena.done:
            img = arena.render()
            opp = tracker.update(img, arena.time)
            z = REST_LOGIT + instinct.logits(opp, arena.width, 1.0, arena.time) + persistence_logits(prev)
            prev = (rng.random(NUM_ACTIONS) < 1 / (1 + np.exp(-np.clip(z, -4, 4)))).astype(np.float32)
            ctl.apply({ACTION_NAMES[i] for i in np.flatnonzero(prev)}, arena.time)
            cam.update((opp.dx, opp.dy) if opp.visible else None, arena.time)
            arena.step(inp)
        return arena.stats["dealt"] - arena.stats["taken"]

    def test_instincts_fight_better_than_random_presses(self):
        seeds = range(3)
        with_instincts = np.mean([self.fight(1.0, s) for s in seeds])
        without = np.mean([self.fight(0.0, s) for s in seeds])
        self.assertGreater(with_instincts, without)


class TestCalibration(unittest.TestCase):
    def test_boxes_become_config(self):
        shot = np.full((300, 400, 3), 80, dtype=np.uint8)
        shot[270:280, 20:140] = (60, 200, 60)
        values = calibration_from_boxes(shot, {"self_bar": (20, 270, 120, 10), "enemy_bar": None,
                                               "self_zone": (150, 160, 60, 120)})
        bar = values["hp_bars"]["self"]
        self.assertEqual(len(bar["roi"]), 4)
        self.assertAlmostEqual(bar["roi"][0], 20 / 400)
        self.assertEqual(bar["color"], [60, 200, 60])
        self.assertNotIn("enemy", values["hp_bars"])
        self.assertAlmostEqual(values["self_zone"][3], 280 / 300)
        self.assertAlmostEqual(bar_fill(shot, bar["roi"], bar["color"]), 1.0)


class TestEpisodes(unittest.TestCase):
    def test_final_reward_is_credited_and_traces_cleared(self):
        learner = FlyLearner(20, NUM_ACTIONS, seed=0)
        x = np.zeros(20, dtype=np.float32)
        x[:5] = 0.5
        mask = np.zeros(NUM_ACTIONS, dtype=np.float32)
        mask[ACTION_NAMES.index("melee")] = 1
        before = learner.policy(x)[ACTION_NAMES.index("melee")]
        learner.update(x, mask, 0.0)
        learner.end_episode(5.0)                 # the knockout
        self.assertGreater(learner.policy(x)[ACTION_NAMES.index("melee")], before)
        self.assertIsNone(learner.prev_x)
        self.assertFalse(np.any(learner.actor_trace))


if __name__ == "__main__":
    unittest.main()
