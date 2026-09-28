"""How the fly learns from what happens in the game.

The learner reads the fly's descending neurons (the brain's commands to the body) as a
vector of firing rates `x` and turns it into key presses:

* Actor: every action is an independent coin flip. Its odds come from the brain's own
  motor populations (the innate drive, computed by the caller) plus learned weights on
  the descending neurons. Sampling keeps the fly exploring instead of repeating one
  move forever.
* Critic: a learned estimate of the reward that is coming, V(x).
* Dopamine: the reward-prediction error  delta = r + gamma * V(x') - V(x),  which is
  what real dopamine neurons signal. It gates a three-factor rule (neuron activity x
  action taken x dopamine) through eligibility traces, so a hit that lands a moment
  after the attack still reinforces the attack, and an expected hit teaches nothing new.

Imitation (Train mode) fits the same actor to the player's key presses with the delta
rule, so watching you play and learning from rewards improve one and the same policy.
"""
import os
from collections import deque

import numpy as np

# Old releases saved raw Hebbian co-activation counts (clipped to +-2) with no sidecar
# file. Those are rescaled on load so they bias the new policy without saturating it.
LEGACY_WEIGHT_SCALE = 0.02
FORMAT_VERSION = 2


def sidecar_path(weights_path):
    """Where the rest of the learner (critic, biases) lives next to fly_weights.npy."""
    root, _ = os.path.splitext(weights_path)
    return root + "_learner.npz"


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def _fit(array, shape):
    """`array` copied into a zero array of `shape` (overlapping part only).

    The readout lists the descending neurons first, so weights saved when the fly read
    only its descending neurons land on the same neurons in a larger readout.
    """
    array = np.asarray(array, dtype=np.float32)
    if array.shape == tuple(shape):
        return array
    out = np.zeros(shape, dtype=np.float32)
    region = tuple(slice(0, min(a, b)) for a, b in zip(array.shape, shape))
    out[region] = array[region]
    return out


class FlyLearner:
    """Actor-critic over descending-neuron firing rates (values in 0..1)."""

    def __init__(self, num_inputs, num_actions, lr=0.05, value_lr=0.1, imitation_lr=0.05,
                 gamma=0.95, lam=0.9, weight_decay=5e-5, max_logit=4.0, seed=None):
        self.num_inputs = num_inputs
        self.num_actions = num_actions
        self.lr = lr
        self.value_lr = value_lr
        self.imitation_lr = imitation_lr
        self.gamma = gamma
        self.lam = lam
        self.weight_decay = weight_decay
        self.max_logit = max_logit
        self.rng = np.random.default_rng(seed)

        self.action_weights = np.zeros((num_inputs, num_actions), dtype=np.float32)
        self.action_bias = np.zeros(num_actions, dtype=np.float32)
        self.value_weights = np.zeros(num_inputs, dtype=np.float32)
        self.value_bias = 0.0
        # Running mean of |x|^2 + 1: step sizes are divided by it, so learning speed does
        # not depend on how many neurons happen to be active. None until the first input.
        self.input_norm = None

        self.reset_traces()
        self.dopamine = 0.0
        self.value = 0.0
        self.dopamine_history = deque(maxlen=100)
        self.reward_history = deque(maxlen=100)
        self.total_reward = 0.0
        self.updates = 0
        self.imitation_updates = 0

    def reset_traces(self):
        """Forget the recent past, e.g. at the start of a session."""
        self.actor_trace = np.zeros((self.num_inputs, self.num_actions), dtype=np.float32)
        self.bias_trace = np.zeros(self.num_actions, dtype=np.float32)
        self.value_trace = np.zeros(self.num_inputs, dtype=np.float32)
        self.value_bias_trace = 0.0
        self.prev_x = None

    # ---- acting -------------------------------------------------------------------------

    def logits(self, x, innate=None):
        z = np.asarray(x, dtype=np.float32) @ self.action_weights + self.action_bias
        if innate is not None:
            z = z + innate
        return np.clip(z, -self.max_logit, self.max_logit)

    def policy(self, x, innate=None):
        """Probability of pressing each action this frame."""
        return _sigmoid(self.logits(x, innate))

    def act(self, x, innate=None):
        """Sample actions. Returns (0/1 mask, probabilities)."""
        probs = self.policy(x, innate)
        mask = (self.rng.random(self.num_actions) < probs).astype(np.float32)
        return mask, probs

    def value_of(self, x):
        return float(np.asarray(x, dtype=np.float32) @ self.value_weights + self.value_bias)

    # ---- learning -----------------------------------------------------------------------

    def _track_input_size(self, x):
        size = float(x @ x) + 1.0
        self.input_norm = size if self.input_norm is None else 0.99 * self.input_norm + 0.01 * size
        return 1.0 / self.input_norm

    def _critic_step(self, x, reward):
        """TD(lambda) for the critic. Returns (TD error or None, step size)."""
        step = self._track_input_size(x)
        delta = None
        if self.prev_x is not None:
            # Both values with the current weights (semi-gradient TD).
            delta = reward + self.gamma * self.value_of(x) - self.value_of(self.prev_x)
            delta = float(np.clip(delta, -5.0, 5.0))
            self.value_weights += (self.value_lr * step * delta) * self.value_trace
            self.value_bias += self.value_lr * step * delta * self.value_bias_trace
        decay = self.gamma * self.lam
        self.value_trace *= decay
        self.value_trace += x
        self.value_bias_trace = self.value_bias_trace * decay + 1.0
        self.prev_x = x
        self.value = self.value_of(x)
        return delta, step

    def update(self, brain_state, actions_taken_mask, reward, probs=None, innate=None):
        """One reinforcement step, called once per frame.

        `reward` is what happened since the previous frame, so it is credited (through the
        eligibility traces) to the actions taken before now; `actions_taken_mask` and
        `probs` are this frame's choice and enter the traces for future rewards.
        Returns the dopamine (TD error) this step produced.
        """
        x = np.asarray(brain_state, dtype=np.float32)
        mask = np.asarray(actions_taken_mask, dtype=np.float32)
        if probs is None:
            probs = self.policy(x, innate)

        delta, step = self._critic_step(x, reward)
        if delta is not None:
            self.action_weights += (self.lr * step * delta) * self.actor_trace
            self.action_bias += (self.lr * step * delta) * self.bias_trace
            if self.weight_decay:
                # Without a consistent reward signal, drift back toward the innate policy.
                self.action_weights *= 1.0 - self.weight_decay
                self.action_bias *= 1.0 - self.weight_decay
            self.updates += 1
        self.dopamine = float(np.clip(delta or 0.0, -2.0, 2.0))

        # Eligibility of this frame's choice: gradient of log-probability, (a - p) x.
        decay = self.gamma * self.lam
        grad = mask - probs
        self.actor_trace *= decay
        self.actor_trace += np.outer(x, grad)
        self.bias_trace = self.bias_trace * decay + grad

        self.dopamine_history.append(self.dopamine)
        self.reward_history.append(reward)
        self.total_reward += reward
        return self.dopamine

    def end_episode(self, reward):
        """A fight is over: credit its final reward (a kill, a death) with nothing to follow,
        then forget the traces so the next fight starts clean."""
        if self.prev_x is not None:
            step = 1.0 / (self.input_norm or 1.0)
            delta = float(np.clip(reward - self.value_of(self.prev_x), -5.0, 5.0))
            self.value_weights += (self.value_lr * step * delta) * self.value_trace
            self.value_bias += self.value_lr * step * delta * self.value_bias_trace
            self.action_weights += (self.lr * step * delta) * self.actor_trace
            self.action_bias += (self.lr * step * delta) * self.bias_trace
            self.dopamine = float(np.clip(delta, -2.0, 2.0))
            self.updates += 1
        self.reward_history.append(reward)
        self.total_reward += reward
        self.reset_traces()

    def imitate(self, brain_state, target_mask, reward=None, innate=None):
        """Behaviour cloning: nudge the policy toward the keys the player is holding.

        If `reward` is given, the critic also learns what the player's play is worth, so
        Play mode starts with a sensible reward baseline.
        """
        x = np.asarray(brain_state, dtype=np.float32)
        target = np.asarray(target_mask, dtype=np.float32)
        probs = self.policy(x, innate)
        if reward is not None:
            self._critic_step(x, reward)
            self.reward_history.append(reward)
            self.total_reward += reward
        else:
            self._track_input_size(x)
        step = self.imitation_lr / self.input_norm
        error = target - probs
        self.action_weights += step * np.outer(x, error)
        self.action_bias += step * error
        self.imitation_updates += 1
        return probs

    def avg_reward(self):
        if not self.reward_history:
            return 0.0
        return float(np.mean(list(self.reward_history)))

    # ---- memory -------------------------------------------------------------------------

    def save(self, path):
        np.save(path, self.action_weights)
        np.savez(sidecar_path(path), version=FORMAT_VERSION, action_bias=self.action_bias,
                 value_weights=self.value_weights, value_bias=np.float32(self.value_bias),
                 input_norm=np.float32(self.input_norm or 0.0))
        print(f"[RL] Saved weights ({self.updates} RL updates, {self.imitation_updates} imitation "
              f"updates, total reward {self.total_reward:+.1f})")

    def load(self, path):
        try:
            weights = np.load(path).astype(np.float32)
        except FileNotFoundError:
            print("[RL] No saved weights found — starting from scratch.")
            return False
        except Exception as e:
            print(f"[RL] Could not read {path} ({e}) — starting from scratch.")
            return False

        if weights.ndim != 2:
            print(f"[RL] Ignoring weights with unexpected shape {weights.shape}.")
            return False
        resized = weights.shape != (self.num_inputs, self.num_actions)
        if resized:
            print(f"[RL] Fitting saved {weights.shape[0]} x {weights.shape[1]} weights into the current "
                  f"{self.num_inputs} x {self.num_actions} readout")
            weights = _fit(weights, (self.num_inputs, self.num_actions))

        extra_path = sidecar_path(path)
        if os.path.exists(extra_path):
            with np.load(extra_path) as extra:
                self.action_bias = _fit(extra["action_bias"], (self.num_actions,))
                self.value_weights = _fit(extra["value_weights"], (self.num_inputs,))
                self.value_bias = float(extra["value_bias"])
                norm = float(extra["input_norm"])
                # A different readout size means a different input scale: re-measure it.
                self.input_norm = norm if norm >= 1.0 and not resized else None
        else:
            peak = float(np.max(np.abs(weights))) if weights.size else 0.0
            if peak > 0:
                weights *= LEGACY_WEIGHT_SCALE / peak
                print("[RL] Converted weights from an older version of fly-jjs.")
        self.action_weights = weights
        print(f"[RL] Loaded previously learned weights from {path}")
        return True
