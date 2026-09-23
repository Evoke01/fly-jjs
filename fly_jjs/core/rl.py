import time
import os
import numpy as np
import mss
import cv2
import pydirectinput
from collections import deque
from flybrain import FlyBrain, FeatureDetectors

# =====================================================
# FLY BRAIN RL: Dopamine-Driven Combat Learning
#
# A single fly brain that learns to fight in Roblox JJK
# through reinforcement learning. Real dopamine neurons
# (DANs) get injected when the fly lands hits or kills.
#
# Controls:
#   M1    - melee combo
#   1-4   - skills
#   Q     - dash (escape stuns)
#   F     - block
#   R     - special
#   W+W   - sprint
#   G     - awaken
#   WASD  - movement
# =====================================================

print("=" * 55)
print("  FLY BRAIN RL: DOPAMINE-DRIVEN COMBAT LEARNER")
print("=" * 55)

# ── ACTION DEFINITIONS ────────────────────────────────
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

# ── BRAIN INITIALIZATION ─────────────────────────────
print("\n[Brain] Loading connectome...")
brain = FlyBrain(device="cpu")
fd = FeatureDetectors(brain)
dns = brain.cells(["descending_neuron"])
num_dns = len(dns)
print(f"[Brain] {num_dns} descending neurons loaded")

# Dopamine neurons — the real deal from the connectome
dans = brain.cells(["DAN"])
if len(dans) == 0:
    print("[Brain] No DAN neurons found, using DN subset as fallback")
    dans = dns[:50]
print(f"[Brain] {len(dans)} dopamine neurons available")

# Visual neurons (compound eye retina)
vis = brain.cells(["LC4", "LPLC2", "LC16"])
if len(vis) < 128:
    vis = brain.cells(["KenyonCell"])
    if len(vis) < 128:
        vis = dns[:128]
retina_r = vis[:64]
retina_b = vis[64:128]

# ── POPULATION GROUPS ─────────────────────────────────
# Each action is driven by a population of descending neurons
# that "vote" on whether to fire that motor command.
fwd_pop     = dns[0:25]
left_pop    = dns[25:45]
back_pop    = dns[45:60]
right_pop   = dns[60:80]
melee_pop   = dns[80:110]
skill1_pop  = dns[110:125]
skill2_pop  = dns[125:140]
skill3_pop  = dns[140:155]
skill4_pop  = dns[155:170]
dash_pop    = dns[170:190]
block_pop   = dns[190:210]
special_pop = dns[210:230]
sprint_pop  = dns[230:250]
awaken_pop  = dns[250:270]

POPULATIONS = [
    fwd_pop, left_pop, back_pop, right_pop,
    melee_pop, skill1_pop, skill2_pop, skill3_pop, skill4_pop,
    dash_pop, block_pop, special_pop, sprint_pop, awaken_pop,
]

# Base thresholds — how much of a population must fire to trigger action
BASE_THRESHOLDS = {
    "forward": 0.12, "left": 0.12, "back": 0.15, "right": 0.12,
    "melee": 0.18,
    "skill1": 0.22, "skill2": 0.22, "skill3": 0.22, "skill4": 0.22,
    "dash": 0.20, "block": 0.18, "special": 0.25,
    "sprint": 0.28, "awaken": 0.35,
}

# ── WINDOW DETECTION ──────────────────────────────────
print("\n[System] Searching for Roblox window...")
try:
    import pygetwindow as gw
    roblox_windows = [w for w in gw.getWindowsWithTitle("Roblox")
                      if w.width > 200 and w.height > 200]
    if roblox_windows:
        roblox_windows.sort(key=lambda w: w.left)
        win = roblox_windows[0]
        MONITOR = {
            "top": max(0, win.top + 40),
            "left": max(0, win.left + 5),
            "width": win.width - 10,
            "height": win.height - 45,
        }
        print(f"[System] Found Roblox: {MONITOR['width']}x{MONITOR['height']}")
    else:
        raise Exception("No Roblox windows found")
except Exception as e:
    print(f"[System] {e}. Using center of screen fallback.")
    MONITOR = {"top": 240, "left": 560, "width": 800, "height": 600}


# =====================================================
# REWARD SYSTEM — reads actual game UI health bars
# =====================================================
class RewardSystem:
    """
    Detects reward/punishment by tracking ACTUAL HEALTH BARS
    from the game UI, not guessing from brightness/motion.

    From the screenshots we know:
    - Our health: green bar at bottom center (~88-91% of screen height)
    - Enemy health: green bar above their nameplate (floats in scene)
    - Hit VFX: white ring effects near center when we land a hit
    - Our health also shown as small bar in top-right corner

    We sample green pixel counts in these regions and track
    frame-to-frame changes. Health drops = damage events.
    """

    # Cooldowns in frames (~20fps)
    HIT_COOLDOWN   = 15   # 0.75s between hit rewards
    TAKEN_COOLDOWN = 12   # 0.6s between damage events
    KILL_COOLDOWN  = 60   # 3s between kill rewards
    BLOCK_COOLDOWN = 12
    DODGE_COOLDOWN = 10

    def __init__(self):
        self.threat_history = deque(maxlen=30)
        self.idle_counter = 0
        self.last_events = deque(maxlen=5)
        self.total_hits_landed = 0
        self.total_hits_taken = 0
        self.total_kills = 0

        # Cooldown timers
        self.cd_hit = 0
        self.cd_taken = 0
        self.cd_kill = 0
        self.cd_block = 0
        self.cd_dodge = 0

        # Health tracking (0.0 to 1.0)
        self.our_health_history = deque(maxlen=10)
        self.enemy_health_history = deque(maxlen=10)
        self.our_prev_health = 1.0
        self.enemy_prev_health = 1.0

        # Kill state tracking
        self.enemy_visible_frames = 0
        self.enemy_gone_frames = 0

    def _sample_our_health(self, img):
        """
        Sample the player's health bar at the bottom center.
        From screenshots: it's the green bar at ~88-91% height,
        ~38-60% width. We count what fraction of that bar is green.
        """
        h, w = img.shape[:2]
        # Health bar region (percentage-based for any resolution)
        y1 = int(h * 0.875)
        y2 = int(h * 0.905)
        x1 = int(w * 0.38)
        x2 = int(w * 0.60)

        if y2 <= y1 or x2 <= x1:
            return self.our_prev_health

        roi = img[y1:y2, x1:x2, :3]  # BGR, drop alpha
        # Green pixels: G channel high, R and B lower
        g = roi[:, :, 1].astype(float)
        r = roi[:, :, 2].astype(float)
        b = roi[:, :, 0].astype(float)
        green_mask = (g > 80) & (g > r * 1.2) & (g > b * 1.2)

        # Health = fraction of bar that is green
        bar_width = x2 - x1
        # Find the rightmost green column
        col_green = np.any(green_mask, axis=0)
        if np.any(col_green):
            rightmost = np.max(np.where(col_green))
            health = (rightmost + 1) / bar_width
        else:
            health = 0.0

        return np.clip(health, 0.0, 1.0)

    def _sample_enemy_health(self, img):
        """
        Sample the enemy's health bar floating above their nameplate.
        It's a small green bar in the middle area of the screen
        (roughly 30-60% height, 20-80% width — it moves with the enemy).
        We look for any small concentrated green bar in that region.
        Returns health (0-1) and whether an enemy bar was found.
        """
        h, w = img.shape[:2]
        # Search region: middle of screen where nameplates appear
        y1 = int(h * 0.25)
        y2 = int(h * 0.55)
        x1 = int(w * 0.15)
        x2 = int(w * 0.85)

        if y2 <= y1 or x2 <= x1:
            return self.enemy_prev_health, False

        roi = img[y1:y2, x1:x2, :3]
        g = roi[:, :, 1].astype(float)
        r = roi[:, :, 2].astype(float)
        b = roi[:, :, 0].astype(float)

        # Green health bar pixels (bright green, not grass/environment)
        green_mask = (g > 100) & (g > r * 1.5) & (g > b * 1.5)

        # Find horizontal runs of green (health bars are thin horizontal)
        # Look row by row for rows with a solid green streak
        best_row = -1
        best_start = 0
        best_end = 0
        best_len = 0

        # Sample every 2nd row for speed
        for row_idx in range(0, green_mask.shape[0], 2):
            row = green_mask[row_idx, :]
            if not np.any(row):
                continue
            # Find longest run of True
            changes = np.diff(row.astype(int))
            starts = np.where(changes == 1)[0] + 1
            ends = np.where(changes == -1)[0] + 1
            # Handle edge cases
            if row[0]:
                starts = np.concatenate([[0], starts])
            if row[-1]:
                ends = np.concatenate([ends, [len(row)]])

            if len(starts) == 0 or len(ends) == 0:
                continue

            for s, e in zip(starts, ends):
                run_len = e - s
                # Health bars are at least 15px wide but not full screen width
                if 15 < run_len < (x2 - x1) * 0.5 and run_len > best_len:
                    best_len = run_len
                    best_row = row_idx
                    best_start = s
                    best_end = e

        if best_len < 15:
            return 0.0, False  # No enemy health bar found

        # Now estimate health: the green bar's length relative to its
        # expected full width. We approximate full width by looking at the
        # background (gray bar) on the same row.
        row_pixels = roi[best_row, :, :]
        row_g = row_pixels[:, 1].astype(float)
        row_r = row_pixels[:, 2].astype(float)
        row_b = row_pixels[:, 0].astype(float)

        # Gray bar pixels (the "missing health" part)
        gray_mask = ((row_g > 40) & (row_g < 120) &
                     (np.abs(row_g - row_r) < 30) &
                     (np.abs(row_g - row_b) < 30))

        # Look for gray pixels immediately after the green bar
        bar_total_end = best_end
        for px in range(best_end, min(best_end + 200, len(gray_mask))):
            if gray_mask[px]:
                bar_total_end = px
            elif bar_total_end > best_end:
                break  # End of gray region

        total_width = max(bar_total_end - best_start, best_len)
        health = best_len / total_width if total_width > 0 else 1.0

        return np.clip(health, 0.0, 1.0), True

    def _detect_white_vfx(self, img):
        """
        Detect white ring hit effects near screen center.
        From screenshots: hits produce bright white circular VFX.
        """
        h, w = img.shape[:2]
        cx, cy = w // 2, h // 2
        sz = 80
        roi = img[max(0, cy - sz):cy + sz, max(0, cx - sz):cx + sz, :3]

        # White pixels: all channels high (> 200)
        r = roi[:, :, 2].astype(float)
        g = roi[:, :, 1].astype(float)
        b = roi[:, :, 0].astype(float)
        white = (r > 200) & (g > 200) & (b > 200)
        white_ratio = float(np.mean(white))

        # Need a noticeable amount of white (hit VFX are bright)
        return white_ratio > 0.03

    def compute(self, threat, motion, actions, img):
        """
        Compute reward using actual health bar tracking.
        """
        reward = 0.0
        events = []

        self.threat_history.append(threat)

        # Tick cooldowns
        self.cd_hit   = max(0, self.cd_hit - 1)
        self.cd_taken = max(0, self.cd_taken - 1)
        self.cd_kill  = max(0, self.cd_kill - 1)
        self.cd_block = max(0, self.cd_block - 1)
        self.cd_dodge = max(0, self.cd_dodge - 1)

        attacked = "melee" in actions
        skill_used = any(a in actions for a in
                         ["skill1", "skill2", "skill3", "skill4", "special"])

        # ── SAMPLE HEALTH BARS ──
        our_health = self._sample_our_health(img)
        enemy_health, enemy_visible = self._sample_enemy_health(img)
        has_white_vfx = self._detect_white_vfx(img)

        self.our_health_history.append(our_health)
        self.enemy_health_history.append(enemy_health)

        # ── HIT LANDED ──
        # Enemy health dropped since last frame + we attacked or used skill
        enemy_health_drop = self.enemy_prev_health - enemy_health
        if (self.cd_hit == 0
                and enemy_visible
                and enemy_health_drop > 0.02
                and (attacked or skill_used or has_white_vfx)):
            if skill_used:
                reward += 1.5
                events.append(("SKILL HIT", +1.5))
            else:
                reward += 1.0
                events.append(("HIT LANDED", +1.0))
            self.total_hits_landed += 1
            self.cd_hit = self.HIT_COOLDOWN

        # Also detect hits from white VFX when we can't see health bar
        elif (self.cd_hit == 0
              and not enemy_visible
              and has_white_vfx
              and (attacked or skill_used)):
            reward += 0.5  # Lower confidence hit
            events.append(("HIT (VFX)", +0.5))
            self.total_hits_landed += 1
            self.cd_hit = self.HIT_COOLDOWN

        # ── GOT HIT ──
        # Our health dropped since last frame
        our_health_drop = self.our_prev_health - our_health
        if self.cd_taken == 0 and our_health_drop > 0.02:
            # Scale punishment by how much health we lost
            pain = min(our_health_drop * 10.0, 2.0)  # 0.2 to 2.0
            reward -= pain
            events.append(("GOT HIT", -pain))
            self.total_hits_taken += 1
            self.cd_taken = self.TAKEN_COOLDOWN

        # ── SUCCESSFUL BLOCK ──
        # We blocked AND didn't lose health (or lost very little)
        if self.cd_block == 0 and "block" in actions and motion > 0.04:
            if our_health_drop < 0.01:
                reward += 0.5
                events.append(("BLOCKED!", +0.5))
                self.cd_block = self.BLOCK_COOLDOWN

        # ── KILL DETECTED ──
        # Enemy was visible and had health, now they're gone
        if enemy_visible:
            self.enemy_visible_frames += 1
            self.enemy_gone_frames = 0
        else:
            self.enemy_gone_frames += 1

        if (self.cd_kill == 0
                and self.enemy_visible_frames >= 10
                and self.enemy_gone_frames >= 8
                and self.enemy_prev_health < 0.3):
            reward += 5.0
            events.append(("*** KILL ***", +5.0))
            self.total_kills += 1
            self.cd_kill = self.KILL_COOLDOWN
            self.enemy_visible_frames = 0

        # ── SUCCESSFUL DODGE ──
        if self.cd_dodge == 0 and motion > 0.06 and "dash" in actions:
            if our_health_drop < 0.01:  # Dodged and didn't lose health
                reward += 0.3
                events.append(("DODGED", +0.3))
                self.cd_dodge = self.DODGE_COOLDOWN

        # ── IDLE PUNISHMENT ──
        moving_only = actions <= {"forward", "back", "left", "right"}
        if len(actions) == 0 or moving_only:
            self.idle_counter += 1
            if self.idle_counter > 40:
                reward -= 0.2
                events.append(("IDLE", -0.2))
        else:
            self.idle_counter = 0

        # Update previous health for next frame comparison
        self.our_prev_health = our_health
        if enemy_visible:
            self.enemy_prev_health = enemy_health

        for e in events:
            self.last_events.append(e)
        return reward, events


# =====================================================
# FLY LEARNER — eligibility-trace RL with weight memory
# =====================================================
class FlyLearner:
    """
    The reinforcement learning core.
    - Eligibility traces track which neurons were active recently.
    - When reward/punishment arrives, the neurons that were
      recently active get credit/blame.
    - Action weights evolve so the fly repeats rewarded patterns
      and avoids punished ones.
    """

    def __init__(self, num_dns, num_actions, lr=0.001):
        self.num_dns = num_dns
        self.num_actions = num_actions
        self.lr = lr

        # Learnable: DN firing patterns → action biases
        self.action_weights = np.zeros((num_dns, num_actions), dtype=np.float32)

        # Eligibility traces (fading memory of recent activity)
        self.eligibility = np.zeros(num_dns, dtype=np.float32)
        self.action_trace = np.zeros(num_actions, dtype=np.float32)

        # Dopamine level — the fly's emergent "mood"
        self.dopamine = 0.0

        # Stats
        self.reward_history = deque(maxlen=200)
        self.dopamine_history = deque(maxlen=200)
        self.total_reward = 0.0
        self.updates = 0

    def update(self, brain_state, actions_taken_mask, reward):
        """Core RL update each frame."""
        # Decay + accumulate eligibility
        self.eligibility *= 0.95
        self.eligibility += brain_state.astype(np.float32)

        self.action_trace *= 0.90
        self.action_trace += actions_taken_mask.astype(np.float32)

        # Dopamine evolves as exponential moving average of reward
        self.dopamine = self.dopamine * 0.92 + reward * 0.5
        self.dopamine = np.clip(self.dopamine, -2.0, 2.0)
        self.dopamine_history.append(self.dopamine)

        self.reward_history.append(reward)
        self.total_reward += reward

        # Learning rule: only update when something meaningful happened
        if abs(reward) > 0.05:
            # Normalize traces to prevent exploding gradients
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
        """Learned bias for each action given current brain state."""
        scores = brain_state.astype(np.float32) @ self.action_weights
        s_max = np.max(np.abs(scores)) + 1e-8
        return scores / s_max  # Normalize to [-1, 1]

    def avg_reward(self):
        if not self.reward_history:
            return 0.0
        return float(np.mean(list(self.reward_history)))

    def save(self, path):
        np.save(path, self.action_weights)
        print(f"[RL] Saved weights ({self.updates} updates, "
              f"total reward {self.total_reward:+.1f})")

    def load(self, path):
        try:
            self.action_weights = np.load(path)
            print(f"[RL] Loaded previously learned weights from {path}")
            return True
        except FileNotFoundError:
            print("[RL] No saved weights found — starting from scratch.")
            return False


# =====================================================
# VISION PIPELINE
# =====================================================
def get_pixel_grids(img):
    """Downsample screen capture to 8x8 Red and Blue compound-eye retinas."""
    # Split channels (img is BGR or BGRA)
    b = img[:, :, 0].astype(float)
    g = img[:, :, 1].astype(float)
    r = img[:, :, 2].astype(float)
    
    # Calculate "red-ness" and "blue-ness" aggressively
    # Subtracting the maximum of the other colors ensures we only see pure colors
    redness = np.clip(r * 2.0 - np.maximum(g, b) * 1.5, 0, 255).astype(np.uint8)
    blueness = np.clip(b * 2.0 - np.maximum(r, g) * 1.5, 0, 255).astype(np.uint8)
    
    red_small = cv2.resize(redness, (8, 8), interpolation=cv2.INTER_AREA)
    blue_small = cv2.resize(blueness, (8, 8), interpolation=cv2.INTER_AREA)
    
    return red_small.flatten() / 255.0, blue_small.flatten() / 255.0, cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)


def detect_opponent(gray, width, height):
    """Find the brightest blob on screen (proxy for opponent)."""
    y1, y2 = height // 5, height - (height // 5)
    roi = gray[y1:y2, :]
    _, thresh = cv2.threshold(roi, 180, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
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
    """Detect sudden screen changes (being attacked / effects)."""
    if prev is None:
        return 0.0
    return float(np.mean(cv2.absdiff(gray, prev)) / 255.0)


# =====================================================
# BRAIN SIMULATION — one cycle of the connectome
# =====================================================
arousal = 0.0
brain_memory = deque(maxlen=5)
for _ in range(5):
    brain_memory.append(0.0)


def run_brain(opp, threat, pixels_r, pixels_b, motion, dopamine_level):
    """
    Run one simulation step of the fly brain.
    Injects: visual input + retina pixels + motion boost +
             arousal feedback + dopamine signal into DANs.
    Returns: population firing rates, brain state vector,
             fired count, arousal, average activity.
    """
    global arousal

    # ── SENSORY INJECTION ──
    injections = fd.inject(opp=opp, threat=threat)

    # Retina: 8x8 Red and 8x8 Blue grids → visual neurons
    for i in range(64):
        # Increased multiplier from 1.5 to 5.0 to make the fly "see" colors much brighter
        injections.append((retina_r[i], pixels_r[i] * 5.0))
        injections.append((retina_b[i], pixels_b[i] * 5.0))

    # Motion boost — sudden changes excite looming detectors
    if motion > 0.05:
        boost = min(motion * 3.0, 2.0)
        for i in range(min(32, len(retina_r))):
            injections.append((retina_r[i], boost))
            injections.append((retina_b[i], boost))

    # Arousal feedback — agitated fly gets more baseline stimulation
    if arousal > 0.3:
        for dn in dns[:20]:
            injections.append((dn, arousal * 0.5))

    # MOTH-TO-FLAME INSTINCT (For Voting Video)
    # The fly naturally wants to walk forward when it sees bright red or blue
    color_intensity = np.sum(pixels_r) + np.sum(pixels_b)
    if color_intensity > 2.0:
        # Inject excitation directly into the forward descending neurons (fwd_pop)
        for dn in dns[0:25]:
            injections.append((dn, 1.5))

    # ── DOPAMINE INJECTION INTO REAL DAN NEURONS ──
    # This is the core RL mechanism: reward/punishment signals
    # flow through the fly's actual dopaminergic circuitry.
    if abs(dopamine_level) > 0.05:
        magnitude = dopamine_level * 2.0
        # Positive dopamine → excite reward DANs
        if magnitude > 0:
            for dan in dans[:min(50, len(dans))]:
                injections.append((dan, magnitude))
        # Negative dopamine → excite punishment/aversion DANs
        else:
            for dan in dans[min(50, len(dans)):min(100, len(dans))]:
                injections.append((dan, abs(magnitude)))

    # ── SIMULATE CONNECTOME ──
    fired_neurons = brain.step(inject=injections)
    fired_set = set(fired_neurons)

    # ── POPULATION VOTING ──
    pop_rates = []
    for pop in POPULATIONS:
        rate = sum(1 for n in pop if n in fired_set) / len(pop)
        pop_rates.append(rate)

    # Brain state vector (binary: which DNs fired)
    brain_state = np.array(
        [1 if dn in fired_set else 0 for dn in dns], dtype=np.uint8
    )

    # Arousal update (slowly builds with activity)
    activity = len(fired_set) / len(dns)
    brain_memory.append(activity)
    arousal = arousal * 0.95 + activity * 0.15
    arousal = min(arousal, 1.0)

    return pop_rates, brain_state, len(fired_set), arousal, np.mean(list(brain_memory))


# =====================================================
# ACTION EXECUTION — translate brain output to gamepad
# =====================================================
def safe_click(x, y):
    """Click with bounds checking."""
    x = max(50, min(x, 1870))
    y = max(50, min(y, 1030))
    pydirectinput.click(x, y)


def execute_actions(actions):
    """Send the chosen actions to the game as keypresses."""
    # Sprint = double-tap W
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

    # Melee = M1 click at screen center
    if "melee" in actions:
        cx = MONITOR["left"] + MONITOR["width"] // 2
        cy = MONITOR["top"] + MONITOR["height"] // 2
        safe_click(cx, cy)

    # Skills
    for skill, key in [("skill1", "1"), ("skill2", "2"),
                        ("skill3", "3"), ("skill4", "4")]:
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


# =====================================================
# VISUALIZATION — the dashboard
# =====================================================
neuron_heat = np.zeros(num_dns, dtype=np.float32)

POP_LABELS = [
    "FWD", "LEFT", "BACK", "RIGHT",
    "M1", "SK1", "SK2", "SK3", "SK4",
    "DASH", "BLK", "SPEC", "SPRNT", "AWKN",
]
POP_COLORS = [
    (0, 220, 0),   (220, 220, 0),  (100, 100, 220), (0, 220, 220),
    (0, 80, 255),  (255, 100, 0),  (255, 150, 0),   (200, 100, 255),
    (100, 200, 255), (255, 255, 0), (200, 200, 200), (0, 255, 200),
    (0, 180, 0),   (255, 50, 255),
]


def build_panel(brain_state, actions, fired, pop_rates,
                arousal_val, avg_act, pixels_r, pixels_b, learner, reward_sys):
    """Build the full visualization panel with brain + dashboard."""
    global neuron_heat

    # ── Smooth glowing brain heatmap ──
    fired_idx = np.where(brain_state == 1)[0]
    neuron_heat[fired_idx] = 1.0
    neuron_heat *= 0.88  # Smooth decay

    padded = np.pad(neuron_heat, (0, 1332 - num_dns), 'constant')
    grid = (padded.reshape((36, 37)) * 255).astype(np.uint8)
    colored = cv2.applyColorMap(grid, cv2.COLORMAP_INFERNO)
    panel = cv2.resize(colored, (500, 350), interpolation=cv2.INTER_NEAREST)

    # ── Dashboard ──
    dash = np.zeros((340, 500, 3), dtype=np.uint8)

    # Header
    cv2.putText(dash, "FLY BRAIN RL", (10, 25),
                cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 200, 255), 2)
    cv2.putText(dash, f"Active: {fired}/{num_dns}", (280, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1)

    # Red Eye view (what the 8x8 retina sees)
    eye_r = cv2.resize(
        (pixels_r.reshape(8, 8) * 255).astype(np.uint8),
        (50, 50), interpolation=cv2.INTER_NEAREST,
    )
    eye_c_r = cv2.cvtColor(eye_r, cv2.COLOR_GRAY2BGR)
    eye_c_r[:,:,0] = 0 # zero out blue
    eye_c_r[:,:,1] = 0 # zero out green
    cv2.rectangle(eye_c_r, (0, 0), (49, 49), (0, 0, 255), 1)
    dash[5:55, 385:435] = eye_c_r
    
    # Blue Eye view
    eye_b = cv2.resize(
        (pixels_b.reshape(8, 8) * 255).astype(np.uint8),
        (50, 50), interpolation=cv2.INTER_NEAREST,
    )
    eye_c_b = cv2.cvtColor(eye_b, cv2.COLOR_GRAY2BGR)
    eye_c_b[:,:,1] = 0 # zero out green
    eye_c_b[:,:,2] = 0 # zero out red
    cv2.rectangle(eye_c_b, (0, 0), (49, 49), (255, 0, 0), 1)
    dash[5:55, 445:495] = eye_c_b

    # ── DOPAMINE BAR ──
    cv2.putText(dash, "Dopamine:", (10, 52),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    cv2.rectangle(dash, (100, 40), (430, 55), (30, 30, 30), -1)
    dopa_norm = (learner.dopamine + 2.0) / 4.0  # Map [-2, +2] → [0, 1]
    dw = int(330 * np.clip(dopa_norm, 0, 1))
    if learner.dopamine >= 0:
        dopa_color = (0, int(min(dopa_norm * 2, 1.0) * 255), 0)
    else:
        dopa_color = (0, 0, int(min((1.0 - dopa_norm) * 2, 1.0) * 255))
    cv2.rectangle(dash, (100, 40), (100 + dw, 55), dopa_color, -1)
    cv2.line(dash, (265, 38), (265, 57), (255, 255, 255), 1)  # Zero line

    # ── AROUSAL BAR ──
    cv2.putText(dash, "Arousal:", (10, 72),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    cv2.rectangle(dash, (100, 62), (430, 74), (30, 30, 30), -1)
    aw = int(330 * min(arousal_val, 1.0))
    ar = int(min(arousal_val * 2, 1.0) * 255)
    ag = int((1.0 - arousal_val) * 255)
    cv2.rectangle(dash, (100, 62), (100 + aw, 74), (0, ag, ar), -1)

    # ── POPULATION FIRING BARS (2 rows of 7) ──
    bar_y0 = 90
    bar_h = 12
    bar_w = 55

    for idx in range(NUM_ACTIONS):
        row = idx // 7
        col = idx % 7
        x = 10 + col * 70
        y = bar_y0 + row * 28
        rate = pop_rates[idx]
        thresh = BASE_THRESHOLDS[ACTION_NAMES[idx]]
        clr = POP_COLORS[idx]

        cv2.putText(dash, POP_LABELS[idx], (x, y - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.28, (180, 180, 180), 1)
        cv2.rectangle(dash, (x, y), (x + bar_w, y + bar_h), (30, 30, 30), -1)
        fw = int(bar_w * min(rate, 1.0))
        cv2.rectangle(dash, (x, y), (x + fw, y + bar_h), clr, -1)
        tx = x + int(bar_w * thresh)
        cv2.line(dash, (tx, y - 1), (tx, y + bar_h + 1), (255, 255, 255), 1)

    # ── REWARD EVENT LOG ──
    ev_y = 160
    cv2.putText(dash, "Rewards:", (10, ev_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    recent_events = list(reward_sys.last_events)[-3:]
    for i, (evt_name, evt_val) in enumerate(recent_events):
        color = (0, 255, 0) if evt_val > 0 else (0, 0, 255)
        cv2.putText(dash, f"{evt_name} {evt_val:+.1f}",
                    (95 + i * 140, ev_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)

    # ── LEARNING STATS ──
    cv2.putText(dash, f"Avg Reward: {learner.avg_reward():+.3f}", (10, 185),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    cv2.putText(dash, f"Updates: {learner.updates}", (200, 185),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    cv2.putText(dash, f"Total: {learner.total_reward:+.1f}", (350, 185),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

    # ── COMBAT STATS ──
    cv2.putText(dash, f"Hits: {reward_sys.total_hits_landed}", (10, 205),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 0), 1)
    cv2.putText(dash, f"Taken: {reward_sys.total_hits_taken}", (140, 205),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 200), 1)
    cv2.putText(dash, f"Kills: {reward_sys.total_kills}", (280, 205),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

    # ── WEIGHT HEATMAP (learned biases visualized) ──
    cv2.putText(dash, "Weights:", (10, 230),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (160, 160, 160), 1)
    w_abs = np.abs(learner.action_weights)
    w_max = np.max(w_abs) + 1e-8
    w_norm = (w_abs / w_max * 255).astype(np.uint8)
    # Resize to a small visible strip
    w_vis = cv2.resize(w_norm, (NUM_ACTIONS * 8, 30),
                       interpolation=cv2.INTER_NEAREST)
    w_colored = cv2.applyColorMap(w_vis, cv2.COLORMAP_VIRIDIS)
    x0 = 80
    dash[218:248, x0:x0 + NUM_ACTIONS * 8] = w_colored

    # ── DOPAMINE SPARKLINE (mood over time) ──
    if len(learner.dopamine_history) > 2:
        spark_x0, spark_y0 = 250, 225
        spark_w, spark_h = 230, 30
        cv2.rectangle(dash, (spark_x0, spark_y0 - spark_h // 2),
                      (spark_x0 + spark_w, spark_y0 + spark_h // 2),
                      (20, 20, 20), -1)
        dh = list(learner.dopamine_history)
        pts = []
        for j, d in enumerate(dh):
            px = spark_x0 + int(j * spark_w / len(dh))
            py = spark_y0 - int((d / 2.0) * (spark_h // 2))
            py = max(spark_y0 - spark_h // 2, min(py, spark_y0 + spark_h // 2))
            pts.append((px, py))
        if len(pts) > 1:
            cv2.polylines(dash, [np.array(pts, np.int32)], False,
                          (0, 200, 255), 1)
        # Zero line
        cv2.line(dash, (spark_x0, spark_y0),
                 (spark_x0 + spark_w, spark_y0), (80, 80, 80), 1)

    # ── ACTION OUTPUT ──
    action_str = " + ".join(sorted(actions)) if actions else "idle"
    if len(action_str) > 55:
        action_str = action_str[:52] + "..."
    cv2.putText(dash, f">> {action_str}", (10, 280),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

    # ── MOOD (emergent from dopamine level) ──
    if learner.dopamine > 1.0:
        mood, mood_color = "EUPHORIC", (0, 255, 0)
    elif learner.dopamine > 0.3:
        mood, mood_color = "CONFIDENT", (0, 255, 200)
    elif learner.dopamine > -0.3:
        mood, mood_color = "FOCUSED", (200, 200, 200)
    elif learner.dopamine > -1.0:
        mood, mood_color = "FRUSTRATED", (0, 100, 255)
    else:
        mood, mood_color = "SUFFERING", (0, 0, 255)
    cv2.putText(dash, f"Mood: {mood}", (10, 320),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, mood_color, 2)

    return np.vstack((panel, dash))


reward_sys = RewardSystem()
learner = FlyLearner(num_dns, NUM_ACTIONS, lr=0.001)

try:
    learner.load(WEIGHTS_PATH)
except FileNotFoundError:
    pass

# =====================================================
# MAIN LOOP
# =====================================================
def run_rl():
    print("\n" + "=" * 55)
    print("  STARTING IN 5 SECONDS")
    print("  Press Q in the OpenCV window to stop")
    print("  Move mouse to TOP-LEFT CORNER to emergency stop!")
    print("=" * 55)
    time.sleep(5)

    pydirectinput.FAILSAFE = True
    prev_gray = None
    last_save_time = time.time()

    with mss.mss() as sct:
        step = 0
        while True:
            loop_start = time.time()

            # ── 1. CAPTURE ──
            img = np.array(sct.grab(MONITOR))

            # ── 2. VISION ──
            pixels_r, pixels_b, gray = get_pixel_grids(img)
            opp, threat = detect_opponent(gray, MONITOR["width"], MONITOR["height"])
            motion = detect_motion(gray, prev_gray)
            prev_gray = gray.copy()

            # ── 3. BRAIN STEP ──
            # Feed current dopamine level back into DANs
            pop_rates, brain_state, fired, arousal_val, avg_act = run_brain(
                opp, threat, pixels_r, pixels_b, motion, learner.dopamine
            )

            # ── 4. ACTION DECISION ──
            # = population voting (instinct) + learned bias (experience)
            learned_scores = learner.get_action_scores(brain_state)

            actions = set()
            action_mask = np.zeros(NUM_ACTIONS, dtype=np.float32)

            for i, name in enumerate(ACTION_NAMES):
                combined = pop_rates[i] + learned_scores[i] * 0.5
                threshold = BASE_THRESHOLDS[name]

                # Arousal lowers thresholds for aggression
                if name in ("forward", "left", "right", "melee"):
                    threshold *= (1.0 - arousal_val * 0.3)

                if combined > threshold:
                    actions.add(name)
                    action_mask[i] = 1.0

            # ── 5. COMPUTE REWARD ──
            reward, events = reward_sys.compute(threat, motion, actions, img)

            # Print significant events
            if events:
                for evt_name, evt_val in events:
                    symbol = "+" if evt_val > 0 else ""
                    print(f"[{step:05d}] {evt_name} ({symbol}{evt_val:.1f})  "
                          f"dopamine={learner.dopamine:+.2f}")

            # ── 6. RL UPDATE ──
            learner.update(brain_state, action_mask, reward)

            # ── 7. EXECUTE ──
            try:
                execute_actions(actions)
            except pydirectinput.FailSafeException:
                print("\n[!] FAILSAFE TRIGGERED! Emergency stop.")
                learner.save(WEIGHTS_PATH)
                break

            # ── 8. VISUALIZE ──
            panel = build_panel(brain_state, actions, fired, pop_rates,
                                arousal_val, avg_act, pixels_r, pixels_b, learner, reward_sys)
            cv2.imshow("Fly Brain RL", panel)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\nExperiment terminated by user.")
                learner.save(WEIGHTS_PATH)
                break

            # Auto-save weights every 60 seconds
            if time.time() - last_save_time > 60:
                learner.save(WEIGHTS_PATH)
                last_save_time = time.time()

            # Target ~20fps
            elapsed = time.time() - loop_start
            if elapsed < 0.05:
                time.sleep(0.05 - elapsed)
            step += 1

    cv2.destroyAllWindows()
    print(f"\nSession ended after {step} brain cycles.")
    print(f"Stats: {reward_sys.total_hits_landed} hits landed, "
          f"{reward_sys.total_hits_taken} hits taken, "
          f"{reward_sys.total_kills} kills")
    print(f"Total reward: {learner.total_reward:+.1f}")
    print(f"Final mood: dopamine={learner.dopamine:+.2f}")

if __name__ == '__main__':
    run_rl()
