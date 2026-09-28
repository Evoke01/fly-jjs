"""One frame of the fly playing: see, feel, decide, learn, act.

Used by Play/Manual mode on the real game and by the arena simulator, so both run the
exact same brain, instincts, learning and controls.
"""
from typing import NamedTuple

import numpy as np

from fly_jjs.core.actions import ACTION_NAMES, NUM_ACTIONS
from fly_jjs.core.brain import FlyBody
from fly_jjs.core.combat import REST_LOGIT, Instincts, PatternRecognizer, RewardSystem, persistence_logits
from fly_jjs.core.controls import CameraController, InputController
from fly_jjs.core.learning import FlyLearner
from fly_jjs.core.tracking import FAR_HEIGHT, NEAR_HEIGHT, SELF_ZONE, OpponentTracker
from fly_jjs.core.vision import FlyEyes


class Step(NamedTuple):
    actions: set
    mask: np.ndarray
    probs: np.ndarray
    reward: float
    events: list
    opponent: object
    pop_rates: np.ndarray
    rates: np.ndarray
    pattern_burst: bool
    camera: tuple


class FlyAgent:
    def __init__(self, components, cfg, width, height, backend, learn=True, readout=None, seed=None):
        self.width, self.height = width, height
        self.learn = learn
        self.eyes = FlyEyes(components.brain, cfg.get("resolution", "64x48"), cfg.get("use_color", True),
                            frame_aspect=width / height)
        if readout is None and cfg.get("readout", "full") == "descending":
            readout = components.dns
        self.body = FlyBody(components, self.eyes, steps=cfg.get("brain_steps", 2), readout=readout)
        self.instincts = Instincts(cfg.get("instincts", 1.0), seed=seed)
        self.rewards = RewardSystem(cfg.get("hp_bars"))
        self.tracker = OpponentTracker(width, height, self_zone=cfg.get("self_zone") or SELF_ZONE,
                                       near_height=cfg.get("opponent_near_height", NEAR_HEIGHT),
                                       far_height=cfg.get("opponent_far_height", FAR_HEIGHT),
                                       ignore=[bar["roi"] for bar in self.rewards.bars.values()])
        # Tracker motion has the camera's own turning removed, so a lower bar marks a burst.
        self.pattern = PatternRecognizer(motion_threshold=0.04) if cfg.get("pattern_recognition", True) else None
        self.learner = FlyLearner(self.body.num_inputs, NUM_ACTIONS, seed=seed)
        self.controls = InputController(backend)
        self.camera = CameraController(backend, width, height, sensitivity=cfg.get("camera_sensitivity", 0.3),
                                       hold_right_button=cfg.get("camera_mode", "shiftlock") == "hold_right")
        self.camera_lock = cfg.get("camera_lock_enabled", True)
        self.prev_mask = np.zeros(NUM_ACTIONS, dtype=np.float32)
        self.prev_actions = set()

    def perceive(self, img, now):
        """Track the opponent, drive the brain, and work out the innate odds of each move.
        Returns (opponent, threat, rates, innate logits, motor population rates, burst)."""
        opponent = self.tracker.update(img, now)
        opp, threat = opponent.as_legacy()
        pattern_burst = False
        if self.pattern is not None:
            self.pattern.update(opp[0], threat, self.tracker.scene_motion)
            pattern_burst, _ = self.pattern.predict_burst()

        rates = self.body.step(img, opp, threat, self.learner.dopamine, pattern_burst)
        drive, pop_rates = self.body.innate_drive(rates)
        innate = (REST_LOGIT + drive
                  + self.instincts.logits(opponent, self.width, self.rewards.our_health, now)
                  + persistence_logits(self.prev_mask))
        return opponent, threat, rates, innate, pop_rates, pattern_burst

    def step(self, img, now, manual_reward=0.0):
        """Play one frame: perceive, learn from the last frame's outcome, act."""
        opponent, threat, rates, innate, pop_rates, pattern_burst = self.perceive(img, now)
        # The reward describes what happened since the last frame, so it is credited to the
        # actions taken before now (through the learner's eligibility traces).
        reward, events = self.rewards.compute(threat, self.tracker.scene_motion, self.prev_actions, img,
                                              manual_reward=manual_reward)
        mask, probs = self.learner.act(rates, innate)
        if self.learn:
            self.learner.update(rates, mask, reward, probs=probs)
        actions = {ACTION_NAMES[i] for i in np.flatnonzero(mask)}

        actions = self.controls.apply(actions, now)
        cam = (0, 0)
        if self.camera_lock:
            cam = self.camera.update((opponent.dx, opponent.dy) if opponent.visible else None, now)
        self.prev_mask = mask
        self.prev_actions = actions
        return Step(actions, mask, probs, reward, events, opponent, pop_rates, rates, pattern_burst, cam)

    def watch(self, img, now, player_mask, learn=True):
        """Train mode: perceive, then learn to press what the player pressed (no input sent)."""
        opponent, threat, rates, innate, pop_rates, pattern_burst = self.perceive(img, now)
        reward, events = self.rewards.compute(threat, self.tracker.scene_motion, self.prev_actions, img)
        player_mask = np.asarray(player_mask, dtype=np.float32)
        if learn:
            probs = self.learner.imitate(rates, player_mask, reward=reward, innate=innate)
        else:
            probs = self.learner.policy(rates, innate)
        actions = {ACTION_NAMES[i] for i in np.flatnonzero(player_mask)}
        self.prev_mask = player_mask
        self.prev_actions = actions
        return Step(actions, player_mask, probs, reward, events, opponent, pop_rates, rates, pattern_burst, (0, 0))

    def new_fight(self):
        """Forget the last fight's momentum (arena fights are separate episodes)."""
        self.tracker.reset()
        self.eyes.reset()
        self.camera.reset()
        self.instincts.switch_at = 0.0
        self.learner.reset_traces()
        self.rewards = RewardSystem(self.rewards.bars)
        self.controls.release_all()
        self.controls.reset()
        if self.pattern is not None:
            self.pattern.history.clear()
        self.prev_mask = np.zeros(NUM_ACTIONS, dtype=np.float32)
        self.prev_actions = set()

    def end_fight(self, img):
        """Credit the final frame (the knockout) and close the episode."""
        reward, events = self.rewards.compute(0.0, 0.0, self.prev_actions, img, final=True)
        if self.learn:
            self.learner.end_episode(reward)
        self.controls.release_all()
        return reward, events

    def release(self):
        self.controls.release_all()
