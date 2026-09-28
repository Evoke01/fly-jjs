import time
import threading
from collections import deque
from types import SimpleNamespace

import numpy as np
import mss
import cv2
from flybrain import FlyBrain, FeatureDetectors, Trace

from fly_jjs.core.config import ConfigManager
from fly_jjs.core.learning import FlyLearner
from fly_jjs.core.storage import WEIGHTS_PATH, create_backup_of_weights
from fly_jjs.core.telemetry import TelemetryPublisher
from fly_jjs.core.vision import FlyEyes, detect_motion, detect_opponent, get_pixel_grids  # noqa: F401

ACTION_NAMES = [
    "forward", "left", "back", "right",
    "melee",                                 # M1
    "skill1", "skill2", "skill3", "skill4",  # 1-4
    "dash",                                  # Q
    "block",                                 # F
    "special",                               # R
    "sprint",                                # W+W
    "awaken",                                # G
]
NUM_ACTIONS = len(ACTION_NAMES)

# Innate drive: when an action's motor population fires at its threshold rate, the
# untrained fly presses that key half the time. INNATE_GAIN sets how sharply the odds
# follow the population's rate; FlyLearner adds what the fly has learned on top.
BASE_THRESHOLDS = {
    "forward": 0.12, "left": 0.12, "back": 0.15, "right": 0.12,
    "melee": 0.18,
    "skill1": 0.22, "skill2": 0.22, "skill3": 0.22, "skill4": 0.22,
    "dash": 0.20, "block": 0.18, "special": 0.25,
    "sprint": 0.28, "awaken": 0.35,
}
INNATE_GAIN = 12.0
DN_TAU = 0.1            # seconds: descending neurons are read as a decaying spike trace
DOPAMINE_DRIVE = 0.8    # voltage per step on dopamine neurons at full surprise
MANUAL_REWARD = 1.5
FRAME_SECONDS = 0.05    # 20 game frames per second
STOP_KEY = 27           # ESC. Not Q: the fly presses Q itself to dash.

_components = None


def get_brain_components():
    """Load the connectome once and pick out the neurons the game talks to."""
    global _components
    if _components is None:
        print("\n[Brain] Loading connectome...")
        brain = FlyBrain(device="cpu")
        dns = brain.cells(["descending_neuron"])
        cell_types = [str(t) for t in np.unique(brain.cell_type)]
        # Reward (PAM) and punishment (PPL1) dopamine neurons of the mushroom body.
        reward_dans = brain.cells([t for t in cell_types if t.startswith("PAM")])
        punish_dans = brain.cells([t for t in cell_types if t.startswith("PPL1")])
        pop_size = len(dns) // NUM_ACTIONS
        populations = [slice(i * pop_size, (i + 1) * pop_size) for i in range(NUM_ACTIONS)]
        _components = SimpleNamespace(brain=brain, fd=FeatureDetectors(brain), dns=dns,
                                      reward_dans=reward_dans, punish_dans=punish_dans,
                                      populations=populations)
        print(f"[Brain] {len(dns)} descending neurons across {NUM_ACTIONS} motor populations; "
              f"{len(reward_dans)} reward / {len(punish_dans)} punishment dopamine neurons")
    return _components


class FlyBody:
    """One game frame in, descending-neuron firing rates out.

    `steps` brain steps (20 ms each) are simulated per frame. More steps give the motor
    neurons more spikes to average, so more of what the fly sees reaches its decisions.
    """

    def __init__(self, components, eyes, steps=1):
        self.c = components
        self.eyes = eyes
        self.steps = max(1, int(steps))
        self.trace = Trace(components.brain, idx=components.dns, tau=DN_TAU)
        self.rate_scale = 1.0 - float(self.trace.decay)   # trace -> spikes per step (0..1)
        self.arousal = 0.0
        self.fired = 0
        self.rates = np.zeros(len(components.dns), dtype=np.float32)

    def step(self, img, opp, threat, dopamine=0.0, pattern_burst=False):
        c = self.c
        opp_pos = (opp[0], opp[2]) if opp[2] > 0 else None
        if pattern_burst:
            # A predicted burst is an attack about to land: drive the looming/escape pathway.
            threat = max(threat, 0.8)
        injections = c.fd.inject(opp=opp_pos, threat=threat)
        injections += self.eyes.inject(img)
        if dopamine > 0.05 and len(c.reward_dans):
            injections.append((c.reward_dans, min(dopamine, 1.0) * DOPAMINE_DRIVE))
        elif dopamine < -0.05 and len(c.punish_dans):
            injections.append((c.punish_dans, min(-dopamine, 1.0) * DOPAMINE_DRIVE))

        for _ in range(self.steps):
            fired = c.brain.step(inject=injections)
            self.rates = self.trace.observe(fired) * self.rate_scale
        self.fired = len(fired)
        activity = float(np.mean(self.rates))
        self.arousal = min(self.arousal * 0.95 + activity * 0.15, 1.0)
        return self.rates

    def innate_drive(self, rates):
        """Per-action logits from the motor populations, and the populations' rates."""
        pop_rates = np.array([rates[p].mean() for p in self.c.populations], dtype=np.float32)
        logits = np.empty(NUM_ACTIONS, dtype=np.float32)
        for i, name in enumerate(ACTION_NAMES):
            threshold = BASE_THRESHOLDS[name]
            if name in ("forward", "left", "right", "melee"):
                threshold *= 1.0 - self.arousal * 0.3
            logits[i] = INNATE_GAIN * (pop_rates[i] - threshold)
        return logits, pop_rates


def detect_monitor():
    """Detect game window or fallback to default coordinates."""
    print("\n[System] Searching for game window...")
    try:
        import pygetwindow as gw
        windows = gw.getAllWindows()
        game_windows = [
            w for w in windows
            if any(t in w.title.lower() for t in ["roblox", "sober", "jujutsu"])
            and w.width > 100 and w.height > 100
        ]
        if game_windows:
            game_windows.sort(key=lambda w: w.left)
            win = game_windows[0]
            monitor = {
                "top": max(0, win.top + 40),
                "left": max(0, win.left + 5),
                "width": win.width - 10,
                "height": win.height - 45,
            }
            print(f"[System] Found window '{win.title}': {monitor['width']}x{monitor['height']}")
            return monitor
    except Exception:
        pass
    print("[System] Game window not found. Using screen bounds fallback.")
    return {"top": 240, "left": 560, "width": 800, "height": 600}


class RewardSystem:
    def __init__(self):
        self.prev_our_health = None
        self.prev_enemy_health = None
        self.prev_motion = 0.0
        self.total_hits_landed = 0
        self.total_hits_taken = 0
        self.total_kills = 0

    def _sample_our_health(self, img):
        h, w, _ = img.shape
        bar_roi = img[int(h * 0.88):int(h * 0.94), int(w * 0.05):int(w * 0.35)]
        if bar_roi.size == 0:
            return 1.0
        green_channel = bar_roi[:, :, 1].astype(float)
        red_channel = bar_roi[:, :, 2].astype(float)
        green_mask = (green_channel > 100) & (green_channel > red_channel * 1.2)
        return float(np.mean(green_mask))

    def _sample_enemy_health(self, img):
        h, w, _ = img.shape
        bar_roi = img[int(h * 0.05):int(h * 0.15), int(w * 0.30):int(w * 0.70)]
        if bar_roi.size == 0:
            return 1.0
        red_channel = bar_roi[:, :, 2].astype(float)
        green_channel = bar_roi[:, :, 1].astype(float)
        red_mask = (red_channel > 120) & (red_channel > green_channel * 1.5)
        return float(np.mean(red_mask))

    def _detect_white_vfx(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        bright = (gray > 235).astype(float)
        return float(np.mean(bright))

    def compute(self, threat, motion, actions, img, manual_reward=0.0):
        reward = manual_reward
        events = []

        if manual_reward > 0:
            events.append(f"MANUAL DOPAMINE TREAT (+{manual_reward:.1f})")
        elif manual_reward < 0:
            events.append(f"MANUAL PENALTY (-{abs(manual_reward):.1f})")

        our_hp = self._sample_our_health(img)
        enemy_hp = self._sample_enemy_health(img)

        if self.prev_our_health is not None:
            hp_loss = self.prev_our_health - our_hp
            if hp_loss > 0.05:
                penalty = -1.5
                reward += penalty
                self.total_hits_taken += 1
                events.append(f"TAKEN DAMAGE ({penalty:+.1f})")

        if self.prev_enemy_health is not None:
            enemy_hp_loss = self.prev_enemy_health - enemy_hp
            if enemy_hp_loss > 0.05:
                bonus = +2.0
                reward += bonus
                self.total_hits_landed += 1
                events.append(f"HIT ENEMY ({bonus:+.1f})")

            if self.prev_enemy_health > 0.1 and enemy_hp < 0.02:
                kill_bonus = +5.0
                reward += kill_bonus
                self.total_kills += 1
                events.append(f"KILLED OPPONENT ({kill_bonus:+.1f})")

        self.prev_our_health = our_hp
        self.prev_enemy_health = enemy_hp

        if threat > 0.4 and "melee" in actions:
            reward += 0.3
            events.append("AGGRO MELEE (+0.3)")

        if threat > 0.6 and "block" in actions:
            reward += 0.4
            events.append("TIMELY BLOCK (+0.4)")

        if threat > 0.7 and "dash" in actions:
            reward += 0.3
            events.append("EVASIVE DASH (+0.3)")

        if threat < 0.2 and "forward" in actions:
            reward += 0.15

        if threat < 0.15 and ("melee" in actions or "skill1" in actions):
            reward -= 0.1

        vfx_intensity = self._detect_white_vfx(img)
        if vfx_intensity > 0.15 and "block" in actions:
            reward += 0.5
            events.append("VFX BLOCK (+0.5)")

        if len(actions) == 0:
            reward -= 0.05

        return reward, events


class PatternRecognizer:
    """Tracks sliding windows of movement and opponent positions to predict sequences."""
    def __init__(self, history_len=10):
        self.history = deque(maxlen=history_len)

    def update(self, opp_dx, threat, motion):
        self.history.append((opp_dx, threat, motion))

    def predict_burst(self):
        if len(self.history) < 3:
            return False, 0.0
        recent_motions = [h[2] for h in self.history]
        recent_threats = [h[1] for h in self.history]

        motion_spike = np.mean(recent_motions[-3:]) > 0.15
        threat_rising = recent_threats[-1] > recent_threats[-3] + 0.1
        return (motion_spike and threat_rising), float(np.mean(recent_motions))


class ManualRewards:
    """Manual Reward mode hotkeys: '+' (or '=') gives a treat, '-' a penalty.

    Listens globally, so Roblox keeps focus and the fly keeps playing while you judge
    it. Falls back to keys pressed in the preview window if pynput is unavailable.
    """
    TREAT_KEYS = {"+", "="}
    PENALTY_KEYS = {"-", "_"}
    TREAT_VK, PENALTY_VK = 107, 109     # numpad + and - on Windows

    def __init__(self, amount=MANUAL_REWARD, listen=True):
        self.amount = amount
        self._pending = 0.0
        self._lock = threading.Lock()
        self.listener = None
        self.last = ("", 0.0)            # (label, time) of the last treat/penalty, for display
        if not listen:
            return
        try:
            from pynput import keyboard

            def on_press(key):
                char = getattr(key, "char", None)
                vk = getattr(key, "vk", None)
                if char in self.TREAT_KEYS or vk == self.TREAT_VK:
                    self.give(+self.amount)
                elif char in self.PENALTY_KEYS or vk == self.PENALTY_VK:
                    self.give(-self.amount)

            self.listener = keyboard.Listener(on_press=on_press)
            self.listener.daemon = True
            self.listener.start()
        except Exception as e:
            self.listener = None
            print(f"[Manual] Global hotkeys unavailable ({e}). Press +/- in the preview window instead.")

    def give(self, amount):
        with self._lock:
            self._pending = float(np.clip(self._pending + amount, -3.0, 3.0))
        self.last = ("TREAT +" if amount > 0 else "PENALTY -", time.time())

    def take(self):
        with self._lock:
            amount, self._pending = self._pending, 0.0
        return amount

    def stop(self):
        if self.listener is not None:
            self.listener.stop()


def safe_click(x, y, monitor):
    try:
        import pydirectinput
        x = max(50, min(x, 1870))
        y = max(50, min(y, 1030))
        pydirectinput.click(x, y, _pause=False)
    except Exception:
        pass


def execute_camera_lock(opp, monitor, sensitivity=0.3):
    """Smoothly moves mouse to center camera on opponent dx, dy."""
    if len(opp) < 2:
        return
    dx, dy = opp[0], opp[1]
    if abs(dx) < 15 and abs(dy) < 15:
        return
    move_x = int(dx * sensitivity)
    move_y = int(dy * sensitivity)
    try:
        import pydirectinput
        pydirectinput.moveRel(move_x, move_y, relative=True, _pause=False)
    except Exception:
        pass


def execute_actions(actions, monitor):
    try:
        import pydirectinput
    except Exception:
        return

    if "sprint" in actions:
        pydirectinput.press('w', _pause=False)
        time.sleep(0.03)
        pydirectinput.press('w', _pause=False)
    else:
        if "forward" in actions:
            pydirectinput.press('w', _pause=False)
        if "back" in actions:
            pydirectinput.press('s', _pause=False)

    if "left" in actions:
        pydirectinput.press('a', _pause=False)
    if "right" in actions:
        pydirectinput.press('d', _pause=False)

    if "melee" in actions:
        cx = monitor["left"] + monitor["width"] // 2
        cy = monitor["top"] + monitor["height"] // 2
        safe_click(cx, cy, monitor)

    for skill, key in [("skill1", "1"), ("skill2", "2"), ("skill3", "3"), ("skill4", "4")]:
        if skill in actions:
            pydirectinput.press(key, _pause=False)

    if "dash" in actions:
        pydirectinput.press('q', _pause=False)
    if "block" in actions:
        pydirectinput.press('f', _pause=False)
    if "special" in actions:
        pydirectinput.press('r', _pause=False)
    if "awaken" in actions:
        pydirectinput.press('g', _pause=False)


def draw_panel(title, lines, color=(0, 255, 0)):
    """Small status window: `lines` are (text, (r, g, b)) pairs."""
    panel = np.zeros((40 + 28 * len(lines), 460, 3), dtype=np.uint8)
    cv2.putText(panel, title, (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    for i, (text, rgb) in enumerate(lines):
        cv2.putText(panel, text, (15, 58 + 28 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.45, rgb[::-1], 1)
    return panel


def countdown(window, seconds=3):
    """Open the preview window first, so it can't steal focus from Roblox mid-session."""
    for remaining in range(seconds, 0, -1):
        cv2.imshow(window, draw_panel(f"STARTING IN {remaining}...", [
            ("Click on the Roblox window now!", (255, 255, 0)),
            ("ESC here (or mouse to top-left corner) stops.", (200, 200, 200))]))
        cv2.waitKey(1000)


def run_rl(manual_mode=False):
    cfg = ConfigManager.load_config()
    res_mode = cfg.get("resolution", "64x48")
    use_color = cfg.get("use_color", True)
    cam_lock = cfg.get("camera_lock_enabled", True)
    cam_sens = cfg.get("camera_sensitivity", 0.3)
    use_pattern = cfg.get("pattern_recognition", True)
    brain_steps = cfg.get("brain_steps", 2)

    print("\n" + "=" * 65)
    if manual_mode:
        print("  🧪 MANUAL REWARD MODE (DOPAMINE TREATS & PENALTIES)")
        print(f"  • Press '+' (or '='): treat, reward {MANUAL_REWARD:+.1f}")
        print(f"  • Press '-': penalty, reward {-MANUAL_REWARD:+.1f}")
        print("  • Keys work while Roblox has focus. The fly credits what it just did.")
    else:
        print("  FLY BRAIN RL: DOPAMINE-DRIVEN COMBAT LEARNER")
    print("  ⚠️ IMPORTANT USER GUIDANCE:")
    print("  1. RESIZE ROBLOX WINDOW TO THE SMALLEST POSSIBLE SIZE.")
    print("  2. RECOMMEND AT LEAST 20+ MINUTES OF TRAINING DATA FOR GOOD RESULTS.")
    print(f"  Visual Mode: {res_mode} | Color: {use_color} | Target Lock: {cam_lock} | Brain steps/frame: {brain_steps}")
    print("  To stop: press ESC in the 'Fly Brain RL' window, or move the mouse")
    print("  to the top-left corner of the screen.")
    print("=" * 65)

    components = get_brain_components()
    monitor = detect_monitor()
    eyes = FlyEyes(components.brain, res_mode, use_color, frame_aspect=monitor["width"] / monitor["height"])
    print(f"[Vision] {eyes.num_neurons} visual neurons across both eyes:")
    for line in eyes.describe():
        print(f"         {line}")
    body = FlyBody(components, eyes, steps=brain_steps)

    try:
        import pydirectinput
        pydirectinput.FAILSAFE = True
    except Exception:
        pass

    reward_sys = RewardSystem()
    pattern_rec = PatternRecognizer() if use_pattern else None
    learner = FlyLearner(len(components.dns), NUM_ACTIONS)
    learner.load(WEIGHTS_PATH)
    create_backup_of_weights()
    manual = ManualRewards() if manual_mode else None
    publisher = TelemetryPublisher("manual" if manual_mode else "play")
    window = "Fly Brain RL"

    prev_gray = None
    prev_actions = set()
    events_log = deque(maxlen=8)
    last_save_time = time.time()
    fps = 0.0
    step = 0

    try:
        countdown(window)
        with mss.mss() as sct:
            while True:
                loop_start = time.time()
                img = np.array(sct.grab(monitor))
                gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                opp, threat = detect_opponent(gray, monitor["width"], monitor["height"])
                motion = detect_motion(gray, prev_gray)
                prev_gray = gray

                pattern_burst = False
                if pattern_rec is not None:
                    pattern_rec.update(opp[0], threat, motion)
                    pattern_burst, _ = pattern_rec.predict_burst()

                rates = body.step(img, opp, threat, learner.dopamine, pattern_burst)
                innate, pop_rates = body.innate_drive(rates)

                # The reward describes what happened since the last frame, so it is credited
                # to the actions taken before now (through the learner's eligibility traces).
                manual_reward = manual.take() if manual is not None else 0.0
                reward, events = reward_sys.compute(threat, motion, prev_actions, img, manual_reward=manual_reward)
                mask, probs = learner.act(rates, innate)
                learner.update(rates, mask, reward, probs=probs)
                actions = {ACTION_NAMES[i] for i in np.flatnonzero(mask)}
                events_log.extend(f"{step}: {e}" for e in events)

                execute_actions(actions, monitor)
                if cam_lock and threat > 0.2:
                    execute_camera_lock(opp, monitor, sensitivity=cam_sens)
                prev_actions = actions

                lines = [
                    (f"Step: {step} | Res: {res_mode} | FPS: {fps:4.1f}", (255, 255, 255)),
                    (f"Dopamine (surprise): {learner.dopamine:+.2f}", (0, 200, 255)),
                    (f"Expected reward: {learner.value:+.2f} | Avg: {learner.avg_reward():+.3f}", (200, 200, 255)),
                    (f"Pressing: {', '.join(sorted(actions)) or '-'}", (0, 255, 128)),
                    (f"Pattern burst: {pattern_burst}", (255, 255, 0)),
                ]
                if manual is not None:
                    label, when = manual.last
                    if label and time.time() - when < 1.0:
                        good = label.startswith("TREAT")
                        lines.append((f">>> {label}{MANUAL_REWARD:.1f} <<<", (0, 255, 0) if good else (255, 80, 80)))
                    lines.append(("'+' treat | '-' penalty (works in Roblox)", (180, 180, 180)))
                lines.append(("ESC: stop & save", (150, 150, 150)))
                cv2.imshow(window, draw_panel("MANUAL REWARD MODE" if manual_mode else "FLY BRAIN RL RUNNING", lines))
                key = cv2.waitKey(1) & 0xFF
                if key == STOP_KEY:
                    break
                if manual is not None and manual.listener is None:
                    if key in (ord('+'), ord('=')):
                        manual.give(+MANUAL_REWARD)
                    elif key in (ord('-'), ord('_')):
                        manual.give(-MANUAL_REWARD)

                publisher.publish({
                    "step": step, "fps": fps, "resolution": res_mode,
                    "dn_active_pct": float(np.mean(rates > 0.05) * 100), "fired": body.fired,
                    "dopamine": learner.dopamine, "value": learner.value, "reward": reward,
                    "avg_reward": learner.avg_reward(), "total_reward": learner.total_reward,
                    "actions": {n: float(p) for n, p in zip(ACTION_NAMES, probs)},
                    "pressed": sorted(actions),
                    "innate": {n: float(r) for n, r in zip(ACTION_NAMES, pop_rates)},
                    "vision": {c: float(v) for c, v in eyes.last_drive.items()},
                    "eye_neurons": eyes.num_neurons,
                    "opponent": {"dx": int(opp[0]), "size": int(opp[2]), "threat": float(threat)},
                    "pattern_burst": bool(pattern_burst),
                    "hits": {"landed": reward_sys.total_hits_landed, "taken": reward_sys.total_hits_taken,
                             "kills": reward_sys.total_kills},
                    "events": list(events_log),
                })

                if time.time() - last_save_time > 60:
                    learner.save(WEIGHTS_PATH)
                    last_save_time = time.time()

                elapsed = time.time() - loop_start
                if elapsed < FRAME_SECONDS:
                    time.sleep(FRAME_SECONDS - elapsed)
                fps = 0.9 * fps + 0.1 / max(time.time() - loop_start, 1e-3)
                step += 1
    except KeyboardInterrupt:
        print("\n[RL] Stopped by user.")
    except Exception as e:
        print(f"[RL] Loop ended: {e}")
    finally:
        if manual is not None:
            manual.stop()
        publisher.close()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

    learner.save(WEIGHTS_PATH)
    print(f"\nSession ended after {step} brain cycles.")


if __name__ == '__main__':
    run_rl()
