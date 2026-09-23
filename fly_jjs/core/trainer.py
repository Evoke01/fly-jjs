import time
import os
import numpy as np
import mss
import cv2
from pynput import keyboard
from collections import deque
from flybrain import FlyBrain, FeatureDetectors

# =====================================================
# FLY BRAIN TRAINER — You play, the fly watches & learns
#
# Run this, switch to Roblox, and play normally.
# The fly brain observes your keypresses and learns
# which brain states should map to which actions.
#
# When you're done, press ESC or Q in the OpenCV window.
# The weights save to fly_weights.npy — the same file
# that fly_rl.py loads. So the fly starts its RL
# training with YOUR skills as a baseline.
#
# Controls it watches for:
#   M1    - melee combo (left click)
#   1-4   - skills
#   Q     - dash
#   F     - block
#   R     - special
#   W,A,S,D - movement
#   G     - awaken
# =====================================================

print("=" * 55)
print("  FLY BRAIN TRAINER — IMITATION LEARNING")
print("=" * 55)

# ── Same action map as fly_rl.py ──
ACTION_NAMES = [
    "forward", "left", "back", "right",
    "melee",
    "skill1", "skill2", "skill3", "skill4",
    "dash", "block", "special",
    "sprint", "awaken",
]
NUM_ACTIONS = len(ACTION_NAMES)

# Map keyboard keys → action indices
KEY_TO_ACTION = {
    'w': 0,   # forward
    'a': 1,   # left
    's': 2,   # back
    'd': 3,   # right
    # melee (index 4) is tracked via mouse click
    '1': 5,   # skill1
    '2': 6,   # skill2
    '3': 7,   # skill3
    '4': 8,   # skill4
    'q': 9,   # dash
    'f': 10,  # block
    'r': 11,  # special
    'g': 13,  # awaken
}
MELEE_IDX = 4
SPRINT_IDX = 12

USER_DIR = os.path.expanduser("~/.fly_jjs")
os.makedirs(USER_DIR, exist_ok=True)
WEIGHTS_FILE = "fly_weights.npy"
WEIGHTS_PATH = os.path.join(USER_DIR, WEIGHTS_FILE)

# ── Brain setup (same as fly_rl.py) ──
print("\n[Brain] Loading connectome...")
brain = FlyBrain(device="cpu")
fd = FeatureDetectors(brain)
dns = brain.cells(["descending_neuron"])
num_dns = len(dns)
print(f"[Brain] {num_dns} descending neurons")

vis = brain.cells(["LC4", "LPLC2", "LC16"])
if len(vis) < 128:
    vis = brain.cells(["KenyonCell"])
    if len(vis) < 128:
        vis = dns[:128]
retina_r = vis[:64]
retina_b = vis[64:128]

# ── Window detection ──
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
        raise Exception("No Roblox windows")
except Exception:
    print("[System] Roblox not found. Using center of screen.")
    MONITOR = {"top": 240, "left": 560, "width": 800, "height": 600}

# ── Keyboard + Mouse tracking ──
pressed_keys = set()
mouse_clicking = False
stop_requested = False
last_w_time = 0.0  # For sprint detection


def on_key_press(key):
    global stop_requested, last_w_time
    try:
        k = key.char.lower()
        pressed_keys.add(k)
        if k == 'w':
            last_w_time = time.time()
    except AttributeError:
        if key == keyboard.Key.esc:
            stop_requested = True


def on_key_release(key):
    try:
        pressed_keys.discard(key.char.lower())
    except AttributeError:
        pass


def on_click(x, y, button, pressed):
    global mouse_clicking
    from pynput.mouse import Button
    if button == Button.left:
        mouse_clicking = pressed


kb_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
kb_listener.start()

from pynput import mouse
mouse_listener = mouse.Listener(on_click=on_click)
mouse_listener.start()

# ── Learning weights ──
action_weights = np.zeros((num_dns, NUM_ACTIONS), dtype=np.float32)
try:
    action_weights = np.load(WEIGHTS_PATH)
    print(f"[Trainer] Loaded existing weights from {WEIGHTS_PATH}")
    print("[Trainer] Will continue training on top of them.")
except FileNotFoundError:
    print("[Trainer] No existing weights — starting fresh.")

LEARNING_RATE = 0.005  # Higher than RL because supervised is more stable


def get_pixel_grids(img):
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


# ── Visualization ──
neuron_heat = np.zeros(num_dns, dtype=np.float32)

# Training stats
total_frames = 0
total_updates = 0
action_counts = np.zeros(NUM_ACTIONS, dtype=int)

print("\n" + "=" * 55)
print("  STARTING IN 5 SECONDS")
print("  Play Roblox normally — the fly will watch & learn")
print("  Press Q or ESC to stop and save")
print("=" * 55)
time.sleep(5)

def run_trainer():
    global action_weights, total_frames, total_updates, action_counts
    
    with mss.mss() as sct:
        while True:
            loop_start = time.time()

        # ── 1. Capture ──
        img = np.array(sct.grab(MONITOR))

        # ── 2. Vision ──
        pixels_r, pixels_b, gray = get_pixel_grids(img)
        opp, threat = detect_opponent(gray, MONITOR["width"], MONITOR["height"])

        # ── 3. Brain step (same injections as fly_rl.py) ──
        injections = fd.inject(opp=opp, threat=threat)
        for i in range(64):
            injections.append((retina_r[i], pixels_r[i] * 5.0))
            injections.append((retina_b[i], pixels_b[i] * 5.0))

        fired_neurons = brain.step(inject=injections)
        fired_set = set(fired_neurons)
        brain_state = np.array(
            [1 if dn in fired_set else 0 for dn in dns], dtype=np.uint8
        )

        # ── 4. Read user's current actions ──
        user_actions = np.zeros(NUM_ACTIONS, dtype=np.float32)

        for key_char, action_idx in KEY_TO_ACTION.items():
            if key_char in pressed_keys:
                user_actions[action_idx] = 1.0
                action_counts[action_idx] += 1

        # Melee from mouse click
        if mouse_clicking:
            user_actions[MELEE_IDX] = 1.0
            action_counts[MELEE_IDX] += 1

        # Sprint: W pressed twice within 0.3s (double-tap detection)
        if 'w' in pressed_keys and (time.time() - last_w_time) < 0.15:
            user_actions[SPRINT_IDX] = 1.0
            action_counts[SPRINT_IDX] += 1

        total_frames += 1

        # ── 5. LEARN — supervised weight update ──
        # Only update when the user is actually doing something
        if np.sum(user_actions) > 0:
            # Hebbian rule: strengthen connection between
            # active neurons and user's chosen actions
            bs = brain_state.astype(np.float32)
            bs_norm = bs / (np.max(bs) + 1e-8)

            update = LEARNING_RATE * np.outer(bs_norm, user_actions)
            action_weights += update
            action_weights = np.clip(action_weights, -3.0, 3.0)
            total_updates += 1

        # ── 6. Visualization ──
        fired_idx = np.where(brain_state == 1)[0]
        neuron_heat[fired_idx] = 1.0
        neuron_heat *= 0.88

        padded = np.pad(neuron_heat, (0, 1332 - num_dns), 'constant')
        grid = (padded.reshape((36, 37)) * 255).astype(np.uint8)
        colored = cv2.applyColorMap(grid, cv2.COLORMAP_INFERNO)
        panel = cv2.resize(colored, (500, 300), interpolation=cv2.INTER_NEAREST)

        # Dashboard
        dash = np.zeros((220, 500, 3), dtype=np.uint8)

        cv2.putText(dash, "TRAINING MODE — FLY IS WATCHING YOU",
                    (10, 25), cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 255, 100), 2)
                    
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

        # Show what keys the user is pressing
        active_actions = [ACTION_NAMES[i] for i in range(NUM_ACTIONS)
                          if user_actions[i] > 0]
        action_str = " + ".join(active_actions) if active_actions else "(waiting...)"
        cv2.putText(dash, f"You: {action_str}", (10, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)

        # Stats
        cv2.putText(dash, f"Frames: {total_frames}", (10, 85),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        cv2.putText(dash, f"Learning updates: {total_updates}", (200, 85),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        # Per-action training counts
        bar_y = 110
        bar_h = 10
        max_count = max(np.max(action_counts), 1)
        labels = ["FWD", "L", "BK", "R", "M1", "S1", "S2", "S3", "S4",
                  "DSH", "BLK", "SPC", "SPR", "AWK"]
        colors = [
            (0, 220, 0), (220, 220, 0), (100, 100, 220), (0, 220, 220),
            (0, 80, 255), (255, 100, 0), (255, 150, 0), (200, 100, 255),
            (100, 200, 255), (255, 255, 0), (200, 200, 200), (0, 255, 200),
            (0, 180, 0), (255, 50, 255),
        ]

        for idx in range(NUM_ACTIONS):
            row = idx // 7
            col = idx % 7
            x = 10 + col * 70
            y = bar_y + row * 28
            count = action_counts[idx]
            bar_w = int(55 * count / max_count) if max_count > 0 else 0

            cv2.putText(dash, labels[idx], (x, y - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.28, (180, 180, 180), 1)
            cv2.rectangle(dash, (x, y), (x + 55, y + bar_h), (30, 30, 30), -1)
            if bar_w > 0:
                cv2.rectangle(dash, (x, y), (x + bar_w, y + bar_h),
                              colors[idx], -1)

        # Weight activity heatmap
        w_abs = np.abs(action_weights)
        w_max = np.max(w_abs) + 1e-8
        w_norm = (w_abs / w_max * 255).astype(np.uint8)
        w_vis = cv2.resize(w_norm, (NUM_ACTIONS * 8, 25),
                           interpolation=cv2.INTER_NEAREST)
        full = np.vstack((panel, dash))
        cv2.imshow("Fly Brain Trainer", full)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        if stop_requested:
            break

        elapsed = time.time() - loop_start
        if elapsed < 0.05:
            time.sleep(0.05 - elapsed)

    # ── Save ──
    cv2.destroyAllWindows()
    kb_listener.stop()
    mouse_listener.stop()

    np.save(WEIGHTS_PATH, action_weights)
    print(f"\n[Trainer] Saved weights to {WEIGHTS_PATH}")
    print(f"[Trainer] Trained on {total_frames} frames, {total_updates} updates")
    print(f"\nAction breakdown:")
    for i, name in enumerate(ACTION_NAMES):
        print(f"  {name:>10}: {action_counts[i]} frames")

if __name__ == '__main__':
    run_trainer()

