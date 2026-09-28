"""Fighting instincts, rewards and attack prediction.

Instincts are the fly's innate combat reflexes: small nudges to the odds of each move,
based on where the opponent is and what it is doing (approach when far, strike when
close and facing it, block or dodge an incoming attack, circle to the side). Learning
adds to them, so an untrained fly already fights sensibly and training refines it.
Set "instincts" to 0 in the config for a fly that only has its brain to go on.
"""
from collections import deque

import numpy as np
import cv2

from fly_jjs.core.actions import ACTION_INDEX, NUM_ACTIONS, OPPOSITES

# Odds (logit) of pressing a key with no particular reason to: about one frame in four.
# Instincts, persistence, the brain's drive and learning all add to it. In arena fights
# at difficulty 1.5 a flat -1.0 won 71-81%, -1.5 won 56% and -2.0 won 19%: a fly that
# rarely retreats or blocks unprompted takes far more damage.
REST_LOGIT = -1.0

# How strongly an action that was on last frame tends to stay on (motor persistence).
# Without it, independent coin flips every frame make movement stutter.
PERSISTENCE = {"forward": 2.0, "left": 1.5, "back": 1.5, "right": 1.5, "block": 2.0,
               "sprint": 1.5, "melee": 1.0}
PERSISTENCE_VECTOR = np.array([PERSISTENCE.get(name, 0.0) for name in ACTION_INDEX], dtype=np.float32)

SKILLS = ("skill1", "skill2", "skill3", "skill4")
STRAFE_SECONDS = (1.5, 3.5)   # how long the fly circles one way before switching

# Rewards per full health bar (1.0) of damage, and per knockout.
DAMAGE_DEALT_REWARD = 30.0
DAMAGE_TAKEN_REWARD = 25.0
KO_REWARD = 5.0
IDLE_PENALTY = 0.01
HP_NOISE = 0.004          # smaller health changes are measurement noise
HIT_EVENT = 0.02          # changes at least this big are shown as hits

# Default health bar regions (fractions of the game window: x0, y0, x1, y1).
DEFAULT_HP_BARS = {
    "self": {"roi": [0.05, 0.88, 0.35, 0.94], "color": None},    # green bar, bottom left
    "enemy": {"roi": [0.30, 0.05, 0.70, 0.15], "color": None},   # red bar, top centre
}


class Instincts:
    def __init__(self, strength=1.0, seed=None):
        self.strength = float(strength)
        self.rng = np.random.default_rng(seed)
        self.strafe = 1
        self.switch_at = 0.0

    def logits(self, opponent, width, own_health=1.0, now=0.0):
        """Logit nudges per action for this frame (zeros when instincts are off)."""
        z = np.zeros(NUM_ACTIONS, dtype=np.float32)
        if self.strength <= 0:
            return z
        i = ACTION_INDEX
        if not opponent.visible:
            # Nobody in view: walk and let the camera sweep, don't waste moves.
            z[i["forward"]] += 0.8
            z[i["sprint"]] += 0.3
            z[i["melee"]] -= 1.5
            z[i["block"]] -= 1.5
            z[i["dash"]] -= 1.0
            z[i["jump"]] -= 1.0
            z[i["special"]] -= 2.0
            for s in SKILLS:
                z[i[s]] -= 2.0
            return z * self.strength

        if now >= self.switch_at:
            self.strafe = -self.strafe
            self.switch_at = now + self.rng.uniform(*STRAFE_SECONDS)

        d = opponent.distance                            # 0 = in your face, 1 = far
        attack = opponent.attack
        facing = 1.0 - min(1.0, abs(opponent.dx) / (0.25 * width))

        # Close the distance, but don't run through them.
        z[i["forward"]] += 3.0 * (d - 0.35)
        z[i["back"]] += 1.5 * (0.2 - d)
        z[i["sprint"]] += 2.5 * (d - 0.6)
        z[i["dash"]] += 2.0 * (d - 0.7) + 2.0 * max(0.0, attack - 0.5)
        # Circle them at fighting range.
        z[i["left" if self.strafe < 0 else "right"]] += 0.8 * (1.0 - d)
        # Strike when in reach and facing them, not into their attack.
        z[i["melee"]] += 4.0 * (0.45 - d) * facing - 1.5 * attack
        for s in SKILLS:
            z[i[s]] += 2.0 * (0.6 - d) * facing - 1.0
        z[i["special"]] += 1.5 * (0.4 - d) * facing - 0.5
        # Defend against an incoming hit.
        z[i["block"]] += 4.0 * attack * (1.0 - d) - 1.0
        z[i["jump"]] += 1.5 * attack - 1.0
        if own_health < 0.3:
            z[i["back"]] += 1.0
            z[i["block"]] += 1.0 * (1.0 - d)
        return np.clip(z * self.strength, -4.0, 4.0)


RECIPROCAL_INHIBITION = 2.5   # an action on last frame suppresses its opposite


def persistence_logits(prev_mask):
    """Motor persistence (keep doing what you were doing) with reciprocal inhibition
    between opposite movements (forward/back, left/right), like antagonist muscles."""
    prev = np.asarray(prev_mask, dtype=np.float32)
    z = PERSISTENCE_VECTOR * prev
    for a, b in OPPOSITES:
        ia, ib = ACTION_INDEX[a], ACTION_INDEX[b]
        z[ia] -= RECIPROCAL_INHIBITION * prev[ib]
        z[ib] -= RECIPROCAL_INHIBITION * prev[ia]
    return z


def bar_fill(img, roi, color=None, kind="self", tolerance=70):
    """Fraction of a horizontal health bar that is filled (0..1).

    With a calibrated `color` (B, G, R), a column counts as filled if enough of its
    pixels are close to that colour. Otherwise the defaults look for green (own bar)
    or red (opponent's bar).
    """
    h, w = img.shape[:2]
    x0, y0, x1, y1 = roi
    region = img[int(h * y0):max(int(h * y1), int(h * y0) + 1), int(w * x0):max(int(w * x1), int(w * x0) + 1), :3]
    if region.size == 0:
        return 1.0
    region = region.astype(np.int16)
    if color is not None:
        match = np.abs(region - np.asarray(color, dtype=np.int16)).sum(axis=2) < tolerance
    elif kind == "self":
        g, r = region[:, :, 1], region[:, :, 2]
        match = (g > 100) & (g > r * 1.2)
    else:
        g, r = region[:, :, 1], region[:, :, 2]
        match = (r > 120) & (r > g * 1.5)
    return float((match.mean(axis=0) > 0.3).mean())


def bar_colour(img_bgr):
    """The bar's colour in a tight selection: median of its most saturated pixels."""
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1].ravel()
    pixels = img_bgr.reshape(-1, 3)
    keep = sat >= np.percentile(sat, 50)
    return [int(v) for v in np.median(pixels[keep], axis=0)]


class RewardSystem:
    """Rewards from the game screen: health bars (hits, damage, kills) plus shaping."""

    def __init__(self, hp_bars=None):
        bars = {k: dict(v) for k, v in DEFAULT_HP_BARS.items()}
        for key, value in (hp_bars or {}).items():
            if key in bars and value:
                bars[key].update({k: v for k, v in value.items() if v is not None})
        self.bars = bars
        self._self_hist = deque(maxlen=3)
        self._enemy_hist = deque(maxlen=3)
        self.prev_our_health = None
        self.prev_enemy_health = None
        self.prev_motion = 0.0
        self.total_hits_landed = 0
        self.total_hits_taken = 0
        self.total_kills = 0
        self.total_deaths = 0
        self.our_health = 1.0

    def _sample_our_health(self, img):
        bar = self.bars["self"]
        return bar_fill(img, bar["roi"], bar.get("color"), "self")

    def _sample_enemy_health(self, img):
        bar = self.bars["enemy"]
        return bar_fill(img, bar["roi"], bar.get("color"), "enemy")

    def compute(self, threat, motion, actions, img, manual_reward=0.0, final=False):
        """Reward for what happened since the last frame, and events to show.

        Paid in proportion to health actually lost and dealt (chip damage through a block
        counts too), plus a knockout bonus/penalty. The old per-frame bonuses for blocking,
        dashing or attacking near the opponent are gone: in the arena the fly learned to
        hold block forever to farm them instead of fighting.
        """
        reward = manual_reward
        events = []

        if manual_reward > 0:
            events.append(f"MANUAL DOPAMINE TREAT (+{manual_reward:.1f})")
        elif manual_reward < 0:
            events.append(f"MANUAL PENALTY (-{abs(manual_reward):.1f})")

        # Median of the last three readings: a VFX flickering over a bar isn't a hit. On the
        # last frame of a fight (`final`) there is nothing to wait for: take it as it is.
        self._self_hist.append(self._sample_our_health(img))
        self._enemy_hist.append(self._sample_enemy_health(img))
        our_hp = self._self_hist[-1] if final else float(np.median(self._self_hist))
        enemy_hp = self._enemy_hist[-1] if final else float(np.median(self._enemy_hist))
        self.our_health = our_hp

        if self.prev_our_health is not None:
            lost = self.prev_our_health - our_hp
            if lost > HP_NOISE:
                reward -= DAMAGE_TAKEN_REWARD * lost
                if lost > HIT_EVENT:
                    self.total_hits_taken += 1
                    events.append(f"TAKEN DAMAGE ({-DAMAGE_TAKEN_REWARD * lost:+.1f})")
            if self.prev_our_health > 0.1 and our_hp < 0.02:
                reward -= KO_REWARD
                self.total_deaths += 1
                events.append(f"KNOCKED OUT ({-KO_REWARD:+.1f})")

        if self.prev_enemy_health is not None:
            dealt = self.prev_enemy_health - enemy_hp
            if dealt > HP_NOISE:
                reward += DAMAGE_DEALT_REWARD * dealt
                if dealt > HIT_EVENT:
                    self.total_hits_landed += 1
                    events.append(f"HIT ENEMY ({DAMAGE_DEALT_REWARD * dealt:+.1f})")
            if self.prev_enemy_health > 0.1 and enemy_hp < 0.02:
                reward += KO_REWARD
                self.total_kills += 1
                events.append(f"KILLED OPPONENT ({KO_REWARD:+.1f})")

        self.prev_our_health = our_hp
        self.prev_enemy_health = enemy_hp

        if len(actions) == 0:
            reward -= IDLE_PENALTY
        return reward, events


class PatternRecognizer:
    """Tracks sliding windows of movement and opponent positions to predict sequences."""
    def __init__(self, history_len=10, motion_threshold=0.15):
        self.history = deque(maxlen=history_len)
        self.motion_threshold = motion_threshold

    def update(self, opp_dx, threat, motion):
        self.history.append((opp_dx, threat, motion))

    def predict_burst(self):
        if len(self.history) < 3:
            return False, 0.0
        recent_motions = [h[2] for h in self.history]
        recent_threats = [h[1] for h in self.history]

        motion_spike = np.mean(recent_motions[-3:]) > self.motion_threshold
        threat_rising = recent_threats[-1] > recent_threats[-3] + 0.1
        return (motion_spike and threat_rising), float(np.mean(recent_motions))
