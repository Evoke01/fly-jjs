import time
import os
import shutil
import numpy as np
import mss
import cv2
from collections import deque
from flybrain import FlyBrain, FeatureDetectors

# =====================================================
# FLY BRAIN TRAINER — You play, the fly watches & learns
# =====================================================

ACTION_NAMES = [
    "forward", "left", "back", "right",
    "melee",
    "skill1", "skill2", "skill3", "skill4",
    "dash", "block", "special",
    "sprint", "awaken",
]
NUM_ACTIONS = len(ACTION_NAMES)

KEY_TO_ACTION = {
    'w': 0,   # forward
    'a': 1,   # left
    's': 2,   # back
    'd': 3,   # right
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

# Lazy brain loading
_brain = None
_fd = None
_dns = None
_retina_r = None
_retina_b = None

def get_brain_components():
    global _brain, _fd, _dns, _retina_r, _retina_b
    if _brain is None:
        print("\n[Brain] Loading connectome...")
        _brain = FlyBrain(device="cpu")
        _fd = FeatureDetectors(_brain)
        _dns = _brain.cells(["descending_neuron"])

        vis = _brain.cells(["LC4", "LPLC2", "LC16"])
        if len(vis) < 128:
            vis = _brain.cells(["KenyonCell"])
            if len(vis) < 128:
                vis = _dns[:128]
        _retina_r = vis[:64]
        _retina_b = vis[64:128]
        print(f"[Brain] {len(_dns)} descending neurons loaded")
    return _brain, _fd, _dns, _retina_r, _retina_b


def detect_monitor():
    """Detect game window or fallback to default coordinates."""
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
    """Create a timestamped backup of current fly_weights.npy if it exists."""
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


def run_trainer():
    print("=" * 55)
    print("  FLY BRAIN TRAINER — IMITATION LEARNING")
    print("=" * 55)

    brain, fd, dns, retina_r, retina_b = get_brain_components()
    num_dns = len(dns)
    monitor = detect_monitor()

    # Load weights
    action_weights = np.zeros((num_dns, NUM_ACTIONS), dtype=np.float32)
    try:
        action_weights = np.load(WEIGHTS_PATH)
        print(f"[Trainer] Loaded existing weights from {WEIGHTS_PATH}")
        print("[Trainer] Will continue training on top of them.")
    except FileNotFoundError:
        print("[Trainer] No existing weights — starting fresh.")

    learning_rate = 0.005

    # Keyboard & Mouse tracking setup
    pressed_keys = set()
    mouse_clicking = [False]
    stop_requested = [False]
    last_w_time = [0.0]

    kb_listener = None
    mouse_listener = None
    try:
        from pynput import keyboard, mouse

        def on_key_press(key):
            try:
                k = key.char.lower()
                pressed_keys.add(k)
                if k == 'w':
                    last_w_time[0] = time.time()
            except AttributeError:
                if key == keyboard.Key.esc:
                    stop_requested[0] = True

        def on_key_release(key):
            try:
                pressed_keys.discard(key.char.lower())
            except AttributeError:
                pass

        def on_click(x, y, button, pressed):
            if button == mouse.Button.left:
                mouse_clicking[0] = pressed

        kb_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
        kb_listener.start()
        mouse_listener = mouse.Listener(on_click=on_click)
        mouse_listener.start()
    except Exception as e:
        print(f"[Trainer] Listener initialization notice: {e}")

    neuron_heat = np.zeros(num_dns, dtype=np.float32)
    total_frames = 0
    total_updates = 0
    action_counts = np.zeros(NUM_ACTIONS, dtype=int)

    print("\n" + "=" * 55)
    print("  STARTING IN 3 SECONDS")
    print("  Play normally — the fly will watch & learn")
    print("  Press Q or ESC in preview window to stop and save")
    print("=" * 55)
    time.sleep(3)

    try:
        with mss.mss() as sct:
            while True:
                loop_start = time.time()

                # 1. Capture
                img = np.array(sct.grab(monitor))

                # 2. Vision
                pixels_r, pixels_b, gray = get_pixel_grids(img)
                opp, threat = detect_opponent(gray, monitor["width"], monitor["height"])

                # 3. Brain step
                injections = fd.inject(opp=opp, threat=threat)
                for i in range(64):
                    injections.append((retina_r[i], pixels_r[i] * 5.0))
                    injections.append((retina_b[i], pixels_b[i] * 5.0))

                color_intensity = np.sum(pixels_r) + np.sum(pixels_b)
                if color_intensity > 2.0:
                    for dn in dns[0:25]:
                        injections.append((dn, 1.5))

                fired_neurons = brain.step(inject=injections)
                fired_set = set(fired_neurons)
                brain_state = np.array(
                    [1 if dn in fired_set else 0 for dn in dns], dtype=np.uint8
                )

                # 4. Read user actions
                user_actions = np.zeros(NUM_ACTIONS, dtype=np.float32)
                for key_char, action_idx in KEY_TO_ACTION.items():
                    if key_char in pressed_keys:
                        user_actions[action_idx] = 1.0
                        action_counts[action_idx] += 1

                if mouse_clicking[0]:
                    user_actions[MELEE_IDX] = 1.0
                    action_counts[MELEE_IDX] += 1

                if 'w' in pressed_keys and (time.time() - last_w_time[0]) < 0.15:
                    user_actions[SPRINT_IDX] = 1.0
                    action_counts[SPRINT_IDX] += 1

                total_frames += 1

                # 5. Learn update
                if np.sum(user_actions) > 0:
                    bs = brain_state.astype(np.float32)
                    bs_norm = bs / (np.max(bs) + 1e-8)
                    update = learning_rate * np.outer(bs_norm, user_actions)
                    action_weights += update
                    action_weights = np.clip(action_weights, -3.0, 3.0)
                    total_updates += 1

                # 6. Visualization
                fired_idx = np.where(brain_state == 1)[0]
                neuron_heat[fired_idx] = 1.0
                neuron_heat *= 0.88

                padded = np.pad(neuron_heat, (0, 1332 - num_dns), 'constant')
                grid = (padded.reshape((36, 37)) * 255).astype(np.uint8)
                colored = cv2.applyColorMap(grid, cv2.COLORMAP_INFERNO)
                panel = cv2.resize(colored, (500, 300), interpolation=cv2.INTER_NEAREST)

                dash = np.zeros((220, 500, 3), dtype=np.uint8)
                cv2.putText(dash, "TRAINING MODE — FLY IS WATCHING YOU",
                            (10, 25), cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 255, 100), 2)

                active_actions = [ACTION_NAMES[i] for i in range(NUM_ACTIONS) if user_actions[i] > 0]
                action_str = " + ".join(active_actions) if active_actions else "(waiting...)"
                cv2.putText(dash, f"You: {action_str}", (10, 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)

                cv2.putText(dash, f"Frames: {total_frames}", (10, 85),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                cv2.putText(dash, f"Learning updates: {total_updates}", (200, 85),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

                full = np.vstack((panel, dash))
                try:
                    cv2.imshow("Fly Brain Trainer", full)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord('q'), 27):
                        break
                except Exception:
                    pass

                if stop_requested[0]:
                    break

                elapsed = time.time() - loop_start
                if elapsed < 0.05:
                    time.sleep(0.05 - elapsed)
    except Exception as e:
        print(f"[Trainer] Run loop ended: {e}")

    # Clean up and save
    try:
        cv2.destroyAllWindows()
    except Exception:
        pass

    if kb_listener:
        try:
            kb_listener.stop()
        except Exception:
            pass
    if mouse_listener:
        try:
            mouse_listener.stop()
        except Exception:
            pass

    create_backup_of_weights()
    np.save(WEIGHTS_PATH, action_weights)
    print(f"\n[Trainer] Saved weights to {WEIGHTS_PATH}")
    print(f"[Trainer] Trained on {total_frames} frames, {total_updates} updates")


if __name__ == '__main__':
    run_trainer()
