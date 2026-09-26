import time
import os
import shutil
import numpy as np
import mss
import cv2
from collections import deque
from flybrain import FlyBrain, FeatureDetectors

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

        fwd_pop     = _dns[0:25]
        left_pop    = _dns[25:45]
        back_pop    = _dns[45:60]
        right_pop   = _dns[60:80]
        melee_pop   = _dns[80:110]
        skill1_pop  = _dns[110:125]
        skill2_pop  = _dns[125:140]
        skill3_pop  = _dns[140:155]
        skill4_pop  = _dns[155:170]
        dash_pop    = _dns[170:190]
        block_pop   = _dns[190:210]
        special_pop = _dns[210:230]
        sprint_pop  = _dns[230:250]
        awaken_pop  = _dns[250:270]

        _populations = [
            fwd_pop, left_pop, back_pop, right_pop,
            melee_pop, skill1_pop, skill2_pop, skill3_pop, skill4_pop,
            dash_pop, block_pop, special_pop, sprint_pop, awaken_pop,
        ]
        print(f"[Brain] {len(_dns)} descending neurons loaded successfully")
    return _brain, _fd, _dns, _dans, _retina_r, _retina_b, _populations


def detect_monitor():
    print("\n[System] Searching for game window...")
    try:
        import pygetwindow as gw
        windows = gw.getAllWindows()
        game_windows = [
            w for w in windows
            if any(t in w.title.lower() for t in ["roblox", "sober", "jujutsu"])
            and w.width > 200 and w.height > 200
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
    print("[System] Game window not found. Using center of screen fallback.")
    return {"top": 240, "left": 560, "width": 800, "height": 600}


def create_backup_of_weights():
    if os.path.exists(WEIGHTS_PATH):
        backup_dir = os.path.join(USER_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"fly_weights_{timestamp}.npy")
        try:
            shutil.copy2(WEIGHTS_PATH, backup_path)
            print(f"[Backup] Saved automatic weight backup to {backup_path}")
            return backup_path
        except Exception as e:
            print(f"[Backup] Note: Could not save backup ({e})")
    return None


class RewardSystem:
    HIT_COOLDOWN   = 15
    TAKEN_COOLDOWN = 12
    KILL_COOLDOWN  = 60
    BLOCK_COOLDOWN = 12
    DODGE_COOLDOWN = 10

    def __init__(self):
        self.threat_history = deque(maxlen=30)
        self.idle_counter = 0
        self.last_events = deque(maxlen=5)
        self.total_hits_landed = 0
        self.total_hits_taken = 0
        self.total_kills = 0

        self.cd_hit = 0
        self.cd_taken = 0
        self.cd_kill = 0
        self.cd_block = 0
        self.cd_dodge = 0

        self.our_health_history = deque(maxlen=10)
        self.enemy_health_history = deque(maxlen=10)
        self.our_prev_health = 1.0
        self.enemy_prev_health = 1.0

        self.enemy_visible_frames = 0
        self.enemy_gone_frames = 0

    def _sample_our_health(self, img):
        h, w = img.shape[:2]
        y1, y2 = int(h * 0.875), int(h * 0.905)
        x1, x2 = int(w * 0.38), int(w * 0.60)

        if y2 <= y1 or x2 <= x1:
            return self.our_prev_health

        roi = img[y1:y2, x1:x2, :3]
        g, r, b = roi[:, :, 1].astype(float), roi[:, :, 2].astype(float), roi[:, :, 0].astype(float)
        green_mask = (g > 80) & (g > r * 1.2) & (g > b * 1.2)

        bar_width = x2 - x1
        col_green = np.any(green_mask, axis=0)
        if np.any(col_green):
            rightmost = np.max(np.where(col_green))
            health = (rightmost + 1) / bar_width
        else:
            health = 0.0

        return float(np.clip(health, 0.0, 1.0))

    def _sample_enemy_health(self, img):
        h, w = img.shape[:2]
        y1, y2 = int(h * 0.25), int(h * 0.55)
        x1, x2 = int(w * 0.15), int(w * 0.85)

        if y2 <= y1 or x2 <= x1:
            return self.enemy_prev_health, False

        roi = img[y1:y2, x1:x2, :3]
        g, r, b = roi[:, :, 1].astype(float), roi[:, :, 2].astype(float), roi[:, :, 0].astype(float)
        green_mask = (g > 100) & (g > r * 1.5) & (g > b * 1.5)

        best_row, best_start, best_end, best_len = -1, 0, 0, 0
        for row_idx in range(0, green_mask.shape[0], 2):
            row = green_mask[row_idx, :]
            if not np.any(row):
                continue
            changes = np.diff(row.astype(int))
            starts = np.where(changes == 1)[0] + 1
            ends = np.where(changes == -1)[0] + 1
            if row[0]:
                starts = np.concatenate([[0], starts])
            if row[-1]:
                ends = np.concatenate([ends, [len(row)]])

            if len(starts) == 0 or len(ends) == 0:
                continue

            for s, e in zip(starts, ends):
                run_len = e - s
                if 15 < run_len < (x2 - x1) * 0.5 and run_len > best_len:
                    best_len, best_row, best_start, best_end = run_len, row_idx, s, e

        if best_len < 15:
            return 0.0, False

        row_pixels = roi[best_row, :, :]
        row_g, row_r, row_b = row_pixels[:, 1].astype(float), row_pixels[:, 2].astype(float), row_pixels[:, 0].astype(float)
        gray_mask = ((row_g > 40) & (row_g < 120) & (np.abs(row_g - row_r) < 30) & (np.abs(row_g - row_b) < 30))

        bar_total_end = best_end
        for px in range(best_end, min(best_end + 200, len(gray_mask))):
            if gray_mask[px]:
                bar_total_end = px
            elif bar_total_end > best_end:
                break

        total_width = max(bar_total_end - best_start, best_len)
        health = best_len / total_width if total_width > 0 else 1.0
        return float(np.clip(health, 0.0, 1.0)), True

    def _detect_white_vfx(self, img):
        h, w = img.shape[:2]
        cx, cy = w // 2, h // 2
        sz = 80
        roi = img[max(0, cy - sz):cy + sz, max(0, cx - sz):cx + sz, :3]
        r, g, b = roi[:, :, 2].astype(float), roi[:, :, 1].astype(float), roi[:, :, 0].astype(float)
        white = (r > 200) & (g > 200) & (b > 200)
        return float(np.mean(white)) > 0.03

    def compute(self, threat, motion, actions, img):
        reward = 0.0
        events = []

        self.threat_history.append(threat)

        self.cd_hit   = max(0, self.cd_hit - 1)
        self.cd_taken = max(0, self.cd_taken - 1)
        self.cd_kill  = max(0, self.cd_kill - 1)
        self.cd_block = max(0, self.cd_block - 1)
        self.cd_dodge = max(0, self.cd_dodge - 1)

        attacked = "melee" in actions
        skill_used = any(a in actions for a in ["skill1", "skill2", "skill3", "skill4", "special"])

        our_health = self._sample_our_health(img)
        enemy_health, enemy_visible = self._sample_enemy_health(img)
        has_white_vfx = self._detect_white_vfx(img)

        self.our_health_history.append(our_health)
        self.enemy_health_history.append(enemy_health)

        enemy_health_drop = self.enemy_prev_health - enemy_health
        if (self.cd_hit == 0 and enemy_visible and enemy_health_drop > 0.02 and (attacked or skill_used or has_white_vfx)):
            if skill_used:
                reward += 1.5
                events.append(("SKILL HIT", +1.5))
            else:
                reward += 1.0
                events.append(("HIT LANDED", +1.0))
            self.total_hits_landed += 1
            self.cd_hit = self.HIT_COOLDOWN
        elif (self.cd_hit == 0 and not enemy_visible and has_white_vfx and (attacked or skill_used)):
            reward += 0.5
            events.append(("HIT (VFX)", +0.5))
            self.total_hits_landed += 1
            self.cd_hit = self.HIT_COOLDOWN

        our_health_drop = self.our_prev_health - our_health
        if self.cd_taken == 0 and our_health_drop > 0.02:
            pain = min(our_health_drop * 10.0, 2.0)
            reward -= pain
            events.append(("GOT HIT", -pain))
            self.total_hits_taken += 1
            self.cd_taken = self.TAKEN_COOLDOWN

        if self.cd_block == 0 and "block" in actions and motion > 0.04:
            if our_health_drop < 0.01:
                reward += 0.5
                events.append(("BLOCKED!", +0.5))
                self.cd_block = self.BLOCK_COOLDOWN

        if enemy_visible:
            self.enemy_visible_frames += 1
            self.enemy_gone_frames = 0
        else:
            self.enemy_gone_frames += 1

        if (self.cd_kill == 0 and self.enemy_visible_frames >= 10 and self.enemy_gone_frames >= 8 and self.enemy_prev_health < 0.3):
            reward += 5.0
            events.append(("*** KILL ***", +5.0))
            self.total_kills += 1
            self.cd_kill = self.KILL_COOLDOWN
            self.enemy_visible_frames = 0

        if self.cd_dodge == 0 and motion > 0.06 and "dash" in actions:
            if our_health_drop < 0.01:
                reward += 0.3
                events.append(("DODGED", +0.3))
                self.cd_dodge = self.DODGE_COOLDOWN

        moving_only = actions <= {"forward", "back", "left", "right"}
        if len(actions) == 0 or moving_only:
            self.idle_counter += 1
            if self.idle_counter > 40:
                reward -= 0.2
                events.append(("IDLE", -0.2))
        else:
            self.idle_counter = 0

        self.our_prev_health = our_health
        if enemy_visible:
            self.enemy_prev_health = enemy_health

        for e in events:
            self.last_events.append(e)
        return reward, events


class FlyLearner:
    def __init__(self, num_dns, num_actions, lr=0.001):
        self.num_dns = num_dns
        self.num_actions = num_actions
        self.lr = lr

        self.action_weights = np.zeros((num_dns, num_actions), dtype=np.float32)
        self.eligibility = np.zeros(num_dns, dtype=np.float32)
        self.action_trace = np.zeros(num_actions, dtype=np.float32)
        self.dopamine = 0.0

        self.reward_history = deque(maxlen=200)
        self.dopamine_history = deque(maxlen=200)
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
            print(f"[RL] Loaded previously learned weights from {path}")
            return True
        except FileNotFoundError:
            print("[RL] No saved weights found — starting from scratch.")
            return False


def get_pixel_grids(img):
    b = img[:, :, 0].astype(float)
    g = img[:, :, 1].astype(float)
    r = img[:, :, 2].astype(float)
    
    redness = np.clip(r * 2.0 - np.maximum(g, b) * 1.5, 0, 255).astype(np.uint8)
    blueness = np.clip(b * 2.0 - np.maximum(r, g) * 1.5, 0, 255).astype(np.uint8)
    
    red_small = cv2.resize(redness, (8, 8), interpolation=cv2.INTER_AREA)
    blue_small = cv2.resize(blueness, (8, 8), interpolation=cv2.INTER_AREA)
    
    return red_small.flatten() / 255.0, blue_small.flatten() / 255.0, cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)


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
                dx = cx - (width // 2)
                threat = min(1.0, size / 70.0)
                return (dx, size), threat
    return (0, 12), 0.1


def detect_motion(gray, prev):
    if prev is None:
        return 0.0
    return float(np.mean(cv2.absdiff(gray, prev)) / 255.0)


arousal = 0.0
brain_memory = deque(maxlen=5)
for _ in range(5):
    brain_memory.append(0.0)


def run_brain(opp, threat, pixels_r, pixels_b, motion, dopamine_level):
    global arousal
    brain, fd, dns, dans, retina_r, retina_b, populations = get_brain_components()

    injections = fd.inject(opp=opp, threat=threat)

    for i in range(64):
        injections.append((retina_r[i], pixels_r[i] * 5.0))
        injections.append((retina_b[i], pixels_b[i] * 5.0))

    if motion > 0.05:
        boost = min(motion * 3.0, 2.0)
        for i in range(min(32, len(retina_r))):
            injections.append((retina_r[i], boost))
            injections.append((retina_b[i], boost))

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
    print("\n" + "=" * 55)
    print("  FLY BRAIN RL: DOPAMINE-DRIVEN COMBAT LEARNER")
    print("  STARTING IN 3 SECONDS")
    print("  Press Q in preview window to stop")
    print("=" * 55)
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

                pixels_r, pixels_b, gray = get_pixel_grids(img)
                opp, threat = detect_opponent(gray, monitor["width"], monitor["height"])
                motion = detect_motion(gray, prev_gray)
                prev_gray = gray.copy()

                pop_rates, brain_state, fired, arousal_val, avg_act = run_brain(
                    opp, threat, pixels_r, pixels_b, motion, learner.dopamine
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

                if cv2 is not None:
                    try:
                        # Display preview window
                        panel = np.zeros((300, 400, 3), dtype=np.uint8)
                        cv2.putText(panel, "FLY BRAIN RL RUNNING", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.putText(panel, f"Step: {step}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(panel, f"Dopamine: {learner.dopamine:+.2f}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)
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
