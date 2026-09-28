import unittest

import numpy as np
import cv2

from fly_jjs.core.actions import ACTION_INDEX, NUM_ACTIONS
from fly_jjs.core.combat import (DAMAGE_DEALT_REWARD, KO_REWARD, PERSISTENCE, Instincts, RewardSystem, bar_colour,
                                 bar_fill, persistence_logits)
from fly_jjs.core.tracking import NOBODY, Opponent, OpponentTracker

W, H = 640, 480
RNG = np.random.default_rng(0)
GROUND = cv2.normalize(cv2.GaussianBlur((RNG.random((H, W * 2)) * 255).astype(np.uint8), (0, 0), 4),
                       None, 60, 140, cv2.NORM_MINMAX)


def frame(pan=0, figure=None, colour=(30, 30, 220), height=110):
    img = np.dstack([GROUND[:, pan:pan + W]] * 3 + [np.full((H, W), 255, np.uint8)]).copy()
    if figure is not None:
        x, y = figure
        cv2.rectangle(img, (x, y), (x + height // 3, y + height), colour + (255,), -1)
    return img


class TestOpponentTracker(unittest.TestCase):
    def test_finds_a_colourful_opponent(self):
        tracker = OpponentTracker(W, H)
        for i in range(8):
            opp = tracker.update(frame(figure=(420, 200)), i * 0.05)
        self.assertTrue(opp.visible)
        self.assertAlmostEqual(opp.dx, 420 + 110 // 6 - W / 2, delta=25)

    def test_camera_turning_is_not_an_opponent(self):
        tracker = OpponentTracker(W, H)
        seen = [tracker.update(frame(pan=8 * i), i * 0.05).visible for i in range(15)]
        self.assertFalse(any(seen))
        self.assertLess(tracker.camera_shift[0], 0)       # it measured the turn

    def test_ignores_hud_regions_and_your_own_character(self):
        img = frame()
        img[20:50, 200:440, :3] = (30, 30, 230)          # red health bar at the top
        img[270:420, 220:300, :3] = (30, 30, 230)        # "you", in the self zone
        tracker = OpponentTracker(W, H, self_zone=(0.3, 0.55, 0.52, 0.9), ignore=[(0.3, 0.04, 0.7, 0.11)])
        for i in range(6):
            opp = tracker.update(img, i * 0.05)
        self.assertFalse(opp.visible)

    def test_distance_follows_apparent_size(self):
        distances = []
        for height in (100, 60, 30):
            tracker = OpponentTracker(W, H)
            for i in range(6):
                opp = tracker.update(frame(figure=(300, 150), height=height), i * 0.05)
            distances.append(opp.distance)
        self.assertLess(distances[0], distances[1])
        self.assertLess(distances[1], distances[2])

    def test_approach_looms_and_legacy_view(self):
        tracker = OpponentTracker(W, H)
        for i in range(12):
            opp = tracker.update(frame(figure=(300 - 3 * i, 120 - 4 * i), height=60 + 8 * i), i * 0.05)
        self.assertGreater(opp.loom, 0)
        (dx, dy, size), threat = opp.as_legacy()
        self.assertGreater(size, 0)
        self.assertEqual(NOBODY.as_legacy(), ((0, 0, 0), 0.0))


class TestInstincts(unittest.TestCase):
    def logits(self, **kw):
        opp = Opponent(True, **kw)
        return Instincts(1.0, seed=0).logits(opp, W, own_health=1.0, now=0.0)

    def test_far_away_it_closes_in(self):
        z = self.logits(dx=0, distance=0.95)
        i = ACTION_INDEX
        self.assertGreater(z[i["forward"]], 1.0)
        self.assertGreater(z[i["sprint"]], 0.0)
        self.assertLess(z[i["melee"]], 0.0)

    def test_in_reach_and_facing_it_attacks(self):
        z = self.logits(dx=0, distance=0.1)
        i = ACTION_INDEX
        self.assertGreater(z[i["melee"]], 1.0)
        self.assertLess(z[i["forward"]], 0.0)

    def test_facing_matters(self):
        facing = self.logits(dx=0, distance=0.1)
        sideways = self.logits(dx=W * 0.4, distance=0.1)
        self.assertGreater(facing[ACTION_INDEX["melee"]], sideways[ACTION_INDEX["melee"]])

    def test_incoming_attack_means_block(self):
        calm = self.logits(dx=0, distance=0.15, attack=0.0)
        danger = self.logits(dx=0, distance=0.15, attack=0.9)
        self.assertGreater(danger[ACTION_INDEX["block"]], calm[ACTION_INDEX["block"]] + 2)
        self.assertLess(danger[ACTION_INDEX["melee"]], calm[ACTION_INDEX["melee"]])

    def test_nobody_in_view_means_no_wasted_moves(self):
        z = Instincts(1.0).logits(NOBODY, W)
        self.assertGreater(z[ACTION_INDEX["forward"]], 0)
        for name in ("melee", "skill1", "block"):
            self.assertLess(z[ACTION_INDEX[name]], 0)

    def test_strength_zero_turns_them_off(self):
        self.assertFalse(np.any(Instincts(0.0).logits(Opponent(True, distance=0.1), W)))

    def test_persistence_keeps_movement_going(self):
        prev = np.zeros(NUM_ACTIONS, dtype=np.float32)
        prev[ACTION_INDEX["forward"]] = 1
        z = persistence_logits(prev)
        self.assertEqual(z[ACTION_INDEX["forward"]], PERSISTENCE["forward"])
        self.assertEqual(z[ACTION_INDEX["skill1"]], 0)
        self.assertLess(z[ACTION_INDEX["back"]], 0)              # reciprocal inhibition


def hud(self_hp, enemy_hp, w=400, h=300):
    img = np.full((h, w, 4), 90, dtype=np.uint8)
    img[int(0.88 * h):int(0.94 * h), int(0.05 * w):int(0.05 * w + 0.30 * w * self_hp), :3] = (60, 200, 60)
    img[int(0.07 * h):int(0.12 * h), int(0.30 * w):int(0.30 * w + 0.40 * w * enemy_hp), :3] = (40, 40, 220)
    return img


class TestRewards(unittest.TestCase):
    def test_bar_fill_reads_default_and_calibrated_bars(self):
        img = hud(0.6, 0.25)
        self.assertAlmostEqual(bar_fill(img, [0.05, 0.88, 0.35, 0.94], None, "self"), 0.6, delta=0.05)
        self.assertAlmostEqual(bar_fill(img, [0.30, 0.05, 0.70, 0.15], None, "enemy"), 0.25, delta=0.05)
        purple = np.full((300, 400, 4), 90, dtype=np.uint8)
        purple[100:110, 50:250, :3] = (200, 40, 160)       # a custom bar colour
        colour = bar_colour(purple[100:110, 50:350, :3])
        self.assertAlmostEqual(bar_fill(purple, [50 / 400, 100 / 300, 350 / 400, 110 / 300], colour), 2 / 3, delta=0.05)

    def test_damage_is_paid_in_proportion(self):
        rs = RewardSystem()
        for _ in range(3):
            rs.compute(0.5, 0.0, {"melee"}, hud(1.0, 1.0))
        rewards = [rs.compute(0.5, 0.0, {"melee"}, hud(1.0, 0.8))[0] for _ in range(3)]
        self.assertAlmostEqual(sum(rewards), DAMAGE_DEALT_REWARD * 0.2, delta=0.8)
        self.assertEqual(rs.total_hits_landed, 1)
        lost = [rs.compute(0.5, 0.0, {"melee"}, hud(0.7, 0.8))[0] for _ in range(3)]
        self.assertLess(sum(lost), -5)

    def test_knockouts(self):
        rs = RewardSystem()
        for _ in range(3):
            rs.compute(0.5, 0.0, {"melee"}, hud(1.0, 0.3))
        rewards = [rs.compute(0.5, 0.0, {"melee"}, hud(1.0, 0.0)) for _ in range(3)]
        self.assertEqual(rs.total_kills, 1)
        self.assertTrue(any(f"KILLED OPPONENT (+{KO_REWARD:.1f})" in e for _, ev in rewards for e in ev))

    def test_blocking_near_an_opponent_pays_nothing_by_itself(self):
        """Regression: +0.4 per frame for blocking near the opponent taught the fly to turtle."""
        rs = RewardSystem()
        total = sum(rs.compute(0.9, 0.0, {"block"}, hud(1.0, 1.0))[0] for _ in range(100))
        self.assertAlmostEqual(total, 0.0, places=6)


if __name__ == "__main__":
    unittest.main()
