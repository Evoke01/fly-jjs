import time
import os
import shutil
import numpy as np
import mss
import cv2
from collections import deque
from flybrain import FlyBrain, FeatureDetectors
from fly_jjs.core.config import ConfigManager, RESOLUTION_PRESETS

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
USER_DIR = os.path.expanduser("~/.fly_jjs")
os.makedirs(USER_DIR, exist_ok=True)
WEIGHTS_FILE = "fly_weights.npy"
WEIGHTS_PATH = os.path.join(USER_DIR, WEIGHTS_FILE)

# Lazy connectome loading
_brain = None
_fd = None
_dns = None
_dans = None
_retina_r = None
_retina_b = None
_populations = None

BASE_THRESHOLDS = {
    "forward": 0.12, "left": 0.12, "back": 0.15, "right": 0.12,
    "melee": 0.18,
    "skill1": 0.22, "skill2": 0.22, "skill3": 0.22, "skill4": 0.22,
    "dash": 0.20, "block": 0.18, "special": 0.25,
    "sprint": 0.28, "awaken": 0.35,
}


def get_brain_components():
    global _brain, _fd, _dns, _dans, _retina_r, _retina_b, _populations
    if _brain is None:
        print("\n[Brain] Loading connectome...")
        _brain = FlyBrain(device="cpu")
        _fd = FeatureDetectors(_brain)
        _dns = _brain.cells(["descending_neuron"])

        _dans = _brain.cells(["DAN"])
        if len(_dans) == 0:
            _dans = _dns[:50]

        vis = _brain.cells(["LC4", "LPLC2", "LC16"])
        if len(vis) < 128:
            vis = _brain.cells(["KenyonCell"])
            if len(vis) < 128:
                vis = _dns[:128]
        _retina_r = vis[:64]
        _retina_b = vis[64:128]

        pop_size = len(_dns) // NUM_ACTIONS
        _populations = [
            _dns[i * pop_size: (i + 1) * pop_size]
            for i in range(NUM_ACTIONS)
        ]
        print(f"[Brain] {len(_dns)} descending neurons assigned across {NUM_ACTIONS} motor populations")

    return _brain, _fd, _dns, _dans, _retina_r, _retina_b, _populations


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


def create_backup_of_weights():
    """Create a timestamped backup of current fly_weights.npy if it exists."""
    if os.path.exists(WEIGHTS_PATH):
        backups_dir = os.path.join(USER_DIR, "backups")
        os.makedirs(backups_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = f"fly_weights_backup_{timestamp}.npy"
        backup_path = os.path.join(backups_dir, backup_file)
        try:
            shutil.copy2(WEIGHTS_PATH, backup_path)
            print(f"[Backup] Created automatic backup at {backup_path}")
        except Exception as e:
            print(f"[Backup] Failed to create backup: {e}")


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

    def compute(self, threat, motion, actions, img):
        reward = 0.0
        events = []

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


class FlyLearner:
    def __init__(self, num_dns, num_actions, lr=0.001):
        self.lr = lr
        self.num_dns = num_dns
        self.num_actions = num_actions
        self.action_weights = np.zeros((num_dns, num_actions), dtype=np.float32)
        self.eligibility = np.zeros(num_dns, dtype=np.float32)
        self.action_trace = np.zeros(num_actions, dtype=np.float32)
        self.dopamine = 0.0
        self.dopamine_history = deque(maxlen=100)
        self.reward_history = deque(maxlen=100)
        self.total_reward = 0.0
        self.updates = 0

    def update(self, brain_state, actions_taken_mask, reward):
        self.eligibility *= 0.95
        self.eligibility += brain_state.astype(np.float32)

        self.action_trace *= 0.90
        self.action_trace += actions_taken_mask.astype(np.float32)

        self.dopamine = self.dopamine * 0.92 + reward * 0.5
        self.dopamine = float(np.clip(self.dopamine, -2.0, 2.0))
        self.dopamine_history.append(self.dopamine)

        self.reward_history.append(reward)
        self.total_reward += reward

        if abs(reward) > 0.05:
            e_max = np.max(self.eligibility) + 1e-8
            a_max = np.max(self.action_trace) + 1e-8
            update = self.lr * reward * np.outer(
                self.eligibility / e_max,
                self.action_trace / a_max,
            )
            self.action_weights += update
            self.action_weights = np.clip(self.action_weights, -2.0, 2.0)
            self.updates += 1

    def get_action_scores(self, brain_state):
        scores = brain_state.astype(np.float32) @ self.action_weights
        s_max = np.max(np.abs(scores)) + 1e-8
        return scores / s_max

    def avg_reward(self):
        if not self.reward_history:
            return 0.0
        return float(np.mean(list(self.reward_history)))

    def save(self, path):
        create_backup_of_weights()
        np.save(path, self.action_weights)
        print(f"[RL] Saved weights ({self.updates} updates, total reward {self.total_reward:+.1f})")

    def load(self, path):
        try:
            self.action_weights = np.load(path)
            if self.action_weights.shape != (self.num_dns, self.num_actions):
                print(f"[RL] Reshaping weights matrix to match connectome ({self.num_dns} x {self.num_actions})")
                new_w = np.zeros((self.num_dns, self.num_actions), dtype=np.float32)
                r = min(self.action_weights.shape[0], self.num_dns)
                c = min(self.action_weights.shape[1], self.num_actions)
                new_w[:r, :c] = self.action_weights[:r, :c]
                self.action_weights = new_w
            print(f"[RL] Loaded previously learned weights from {path}")
            return True
        except FileNotFoundError:
            print("[RL] No saved weights found — starting from scratch.")
            return False


def get_pixel_grids(img, resolution_preset="8x8", use_color=True):
    target_wh = RESOLUTION_PRESETS.get(resolution_preset, (8, 8))
    
    if use_color:
        bgr_small = cv2.resize(img[:, :, :3], target_wh, interpolation=cv2.INTER_AREA)
        r_grid = bgr_small[:, :, 2].flatten() / 255.0
        b_grid = bgr_small[:, :, 0].flatten() / 255.0
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        gray_small = cv2.resize(gray, target_wh, interpolation=cv2.INTER_AREA)
        r_grid = gray_small.flatten() / 255.0
        b_grid = gray_small.flatten() / 255.0

    gray_full = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    return r_grid, b_grid, gray_full


def detect_opponent(gray, width, height):
    y1, y2 = height // 5, height - (height // 5)
    roi = gray[y1:y2, :]
    _, thresh = cv2.threshold(roi, 180, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        c = max(contours, key=cv2.contourArea)
        size = int(cv2.contourArea(c) ** 0.5)
        if size > 10:
            M = cv2.moments(c)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"]) + y1
                dx = cx - (width // 2)
                dy = cy - (height // 2)
                threat = min(1.0, size / 70.0)
                return (dx, dy, size), threat
    return (0, 0, 12), 0.1


def detect_motion(gray, prev):
    if prev is None:
        return 0.0
    return float(np.mean(cv2.absdiff(gray, prev)) / 255.0)


arousal = 0.0
brain_memory = deque(maxlen=5)
for _ in range(5):
    brain_memory.append(0.0)


def run_brain(opp, threat, pixels_r, pixels_b, motion, dopamine_level, pattern_burst=False):
    global arousal
    brain, fd, dns, dans, retina_r, retina_b, populations = get_brain_components()

    opp_pos = (opp[0], opp[2]) if len(opp) == 3 else opp
    injections = fd.inject(opp=opp_pos, threat=threat)

    num_r = min(len(pixels_r), len(retina_r))
    for i in range(num_r):
        injections.append((retina_r[i], pixels_r[i] * 5.0))

    num_b = min(len(pixels_b), len(retina_b))
    for i in range(num_b):
        injections.append((retina_b[i], pixels_b[i] * 5.0))

    if motion > 0.05:
        boost = min(motion * 3.0, 2.0)
        for i in range(min(32, len(retina_r))):
            injections.append((retina_r[i], boost))
            injections.append((retina_b[i], boost))

    if pattern_burst:
        for dn in dns[20:40]:
            injections.append((dn, 1.8))

    if arousal > 0.3:
        for dn in dns[:20]:
            injections.append((dn, arousal * 0.5))

    color_intensity = np.sum(pixels_r) + np.sum(pixels_b)
    if color_intensity > 2.0:
        for dn in dns[0:25]:
            injections.append((dn, 1.5))

    if abs(dopamine_level) > 0.05:
        magnitude = dopamine_level * 2.0
        if magnitude > 0:
            for dan in dans[:min(50, len(dans))]:
                injections.append((dan, magnitude))
        else:
            for dan in dans[min(50, len(dans)):min(100, len(dans))]:
                injections.append((dan, abs(magnitude)))

    fired_neurons = brain.step(inject=injections)
    fired_set = set(fired_neurons)

    pop_rates = []
    for pop in populations:
        rate = sum(1 for n in pop if n in fired_set) / len(pop)
        pop_rates.append(rate)

    brain_state = np.array([1 if dn in fired_set else 0 for dn in dns], dtype=np.uint8)

    activity = len(fired_set) / len(dns)
    brain_memory.append(activity)
    arousal = arousal * 0.95 + activity * 0.15
    arousal = min(arousal, 1.0)

    return pop_rates, brain_state, len(fired_set), arousal, np.mean(list(brain_memory))


def safe_click(x, y, monitor):
    try:
        import pydirectinput
        x = max(50, min(x, 1870))
        y = max(50, min(y, 1030))
        pydirectinput.click(x, y)
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


def run_rl():
    cfg = ConfigManager.load_config()
    res_mode = cfg.get("resolution", "8x8")
    use_color = cfg.get("use_color", True)
    cam_lock = cfg.get("camera_lock_enabled", True)
    cam_sens = cfg.get("camera_sensitivity", 0.3)
    use_pattern = cfg.get("pattern_recognition", True)

    print("\n" + "=" * 65)
    print("  FLY BRAIN RL: DOPAMINE-DRIVEN COMBAT LEARNER")
    print("  ⚠️ IMPORTANT USER GUIDANCE:")
    print("  1. RESIZE ROBLOX WINDOW TO THE SMALLEST POSSIBLE SIZE.")
    print("  2. RECOMMEND AT LEAST 20+ MINUTES OF TRAINING DATA FOR GOOD RESULTS.")
    print(f"  Visual Mode: {res_mode} | Color: {use_color} | Target Lock: {cam_lock}")
    print("  STARTING IN 3 SECONDS...")
    print("  Press Q in preview window to stop")
    print("=" * 65)
    time.sleep(3)

    brain, fd, dns, dans, retina_r, retina_b, populations = get_brain_components()
    num_dns = len(dns)
    monitor = detect_monitor()

    try:
        import pydirectinput
        pydirectinput.FAILSAFE = True
    except Exception:
        pass

    reward_sys = RewardSystem()
    pattern_rec = PatternRecognizer() if use_pattern else None
    learner = FlyLearner(num_dns, NUM_ACTIONS, lr=0.001)
    learner.load(WEIGHTS_PATH)

    prev_gray = None
    last_save_time = time.time()
    step = 0

    try:
        with mss.mss() as sct:
            while True:
                loop_start = time.time()

                img = np.array(sct.grab(monitor))

                pixels_r, pixels_b, gray = get_pixel_grids(img, resolution_preset=res_mode, use_color=use_color)
                opp, threat = detect_opponent(gray, monitor["width"], monitor["height"])
                motion = detect_motion(gray, prev_gray)
                prev_gray = gray.copy()

                pattern_burst = False
                if pattern_rec is not None:
                    pattern_rec.update(opp[0], threat, motion)
                    pattern_burst, _ = pattern_rec.predict_burst()

                pop_rates, brain_state, fired, arousal_val, avg_act = run_brain(
                    opp, threat, pixels_r, pixels_b, motion, learner.dopamine, pattern_burst=pattern_burst
                )

                learned_scores = learner.get_action_scores(brain_state)
                actions = set()
                action_mask = np.zeros(NUM_ACTIONS, dtype=np.float32)

                for i, name in enumerate(ACTION_NAMES):
                    combined = pop_rates[i] + learned_scores[i] * 0.5
                    threshold = BASE_THRESHOLDS[name]
                    if name in ("forward", "left", "right", "melee"):
                        threshold *= (1.0 - arousal_val * 0.3)

                    if combined > threshold:
                        actions.add(name)
                        action_mask[i] = 1.0

                reward, events = reward_sys.compute(threat, motion, actions, img)
                learner.update(brain_state, action_mask, reward)

                execute_actions(actions, monitor)

                if cam_lock and threat > 0.2:
                    execute_camera_lock(opp, monitor, sensitivity=cam_sens)

                if cv2 is not None:
                    try:
                        panel = np.zeros((300, 420, 3), dtype=np.uint8)
                        cv2.putText(panel, "FLY BRAIN RL RUNNING", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.putText(panel, f"Step: {step} | Res: {res_mode}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(panel, f"Dopamine: {learner.dopamine:+.2f}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)
                        cv2.putText(panel, f"Pattern Burst: {pattern_burst}", (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                        cv2.imshow("Fly Brain RL", panel)
                        if cv2.waitKey(1) & 0xFF in (ord('q'), 27):
                            learner.save(WEIGHTS_PATH)
                            break
                    except Exception:
                        pass

                if time.time() - last_save_time > 60:
                    learner.save(WEIGHTS_PATH)
                    last_save_time = time.time()

                elapsed = time.time() - loop_start
                if elapsed < 0.05:
                    time.sleep(0.05 - elapsed)
                step += 1
    except Exception as e:
        print(f"[RL] Loop ended: {e}")

    try:
        cv2.destroyAllWindows()
    except Exception:
        pass

    learner.save(WEIGHTS_PATH)
    print(f"\nSession ended after {step} brain cycles.")


if __name__ == '__main__':
    run_rl()
