import time
import os
import shutil
import numpy as np
import mss
import cv2
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

KEY_MAP = {
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
    print("[System] Game window not found. Using center of screen fallback.")
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
                dx = cx - (width // 2)
                threat = min(1.0, size / 70.0)
                return (dx, size), threat
    return (0, 12), 0.1


def run_trainer():
    cfg = ConfigManager.load_config()
    res_mode = cfg.get("resolution", "8x8")
    use_color = cfg.get("use_color", True)

    print("\n" + "=" * 65)
    print("  FLY BRAIN IMITATION TRAINER (SUPERVISED LEARNING)")
    print("  ⚠️ IMPORTANT USER GUIDANCE:")
    print("  1. RESIZE ROBLOX WINDOW TO THE SMALLEST POSSIBLE SIZE.")
    print("  2. RECOMMEND AT LEAST 20+ MINUTES OF TRAINING DATA FOR GOOD RESULTS.")
    print(f"  Visual Mode: {res_mode} | Color: {use_color}")
    print("  STARTING IN 3 SECONDS...")
    print("=" * 65)
    time.sleep(3)

    brain, fd, dns, retina_r, retina_b = get_brain_components()
    num_dns = len(dns)
    monitor = detect_monitor()

    # Load existing weights or start clean
    if os.path.exists(WEIGHTS_PATH):
        try:
            weights = np.load(WEIGHTS_PATH)
            if weights.shape != (num_dns, NUM_ACTIONS):
                weights = np.zeros((num_dns, NUM_ACTIONS), dtype=np.float32)
            print(f"[Trainer] Loaded existing weights from {WEIGHTS_PATH}")
        except Exception:
            weights = np.zeros((num_dns, NUM_ACTIONS), dtype=np.float32)
    else:
        weights = np.zeros((num_dns, NUM_ACTIONS), dtype=np.float32)

    active_keys = set()

    try:
        from pynput import keyboard, mouse

        def on_key_press(key):
            try:
                k = key.char.lower() if hasattr(key, 'char') and key.char else None
                if k in KEY_MAP:
                    active_keys.add(k)
            except Exception:
                pass

        def on_key_release(key):
            try:
                k = key.char.lower() if hasattr(key, 'char') and key.char else None
                if k in active_keys:
                    active_keys.remove(k)
            except Exception:
                pass

        def on_click(x, y, button, pressed):
            if pressed and button == mouse.Button.left:
                active_keys.add("click")
            elif not pressed and "click" in active_keys:
                active_keys.remove("click")

        kb_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
        m_listener = mouse.Listener(on_click=on_click)
        kb_listener.start()
        m_listener.start()
        print("[Trainer] Input listeners activated. Play Roblox now!")

    except Exception as e:
        print(f"[Trainer] Listener warning: {e}. Running in simulation mode.")

    start_time = time.time()
    last_save_time = time.time()
    step = 0
    lr = 0.005

    try:
        with mss.mss() as sct:
            while True:
                loop_start = time.time()

                img = np.array(sct.grab(monitor))

                pixels_r, pixels_b, gray = get_pixel_grids(img, resolution_preset=res_mode, use_color=use_color)
                opp, threat = detect_opponent(gray, monitor["width"], monitor["height"])

                injections = fd.inject(opp=opp, threat=threat)
                num_r = min(len(pixels_r), len(retina_r))
                for i in range(num_r):
                    injections.append((retina_r[i], pixels_r[i] * 5.0))

                num_b = min(len(pixels_b), len(retina_b))
                for i in range(num_b):
                    injections.append((retina_b[i], pixels_b[i] * 5.0))

                fired_neurons = brain.step(inject=injections)
                fired_set = set(fired_neurons)
                brain_state = np.array([1 if dn in fired_set else 0 for dn in dns], dtype=np.float32)

                user_actions = np.zeros(NUM_ACTIONS, dtype=np.float32)
                for k in list(active_keys):
                    if k in KEY_MAP:
                        user_actions[KEY_MAP[k]] = 1.0
                    elif k == "click":
                        user_actions[MELEE_IDX] = 1.0

                if user_actions.sum() > 0:
                    delta = np.outer(brain_state, user_actions) * lr
                    weights += delta
                    weights = np.clip(weights, -2.0, 2.0)

                elapsed_min = (time.time() - start_time) / 60.0
                progress_pct = min(100.0, (elapsed_min / 20.0) * 100.0)

                if cv2 is not None:
                    try:
                        panel = np.zeros((260, 420, 3), dtype=np.uint8)
                        cv2.putText(panel, "FLY IMITATION TRAINER", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                        cv2.putText(panel, f"Step: {step} | Active Keys: {len(active_keys)}", (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(panel, f"Time Played: {elapsed_min:.1f} / 20.0 mins ({progress_pct:.0f}%)", (20, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                        cv2.putText(panel, "Press Q or ESC to stop & save", (20, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                        cv2.imshow("Fly Trainer", panel)
                        if cv2.waitKey(1) & 0xFF in (ord('q'), 27):
                            break
                    except Exception:
                        pass

                if time.time() - last_save_time > 30:
                    create_backup_of_weights()
                    np.save(WEIGHTS_PATH, weights)
                    last_save_time = time.time()

                elapsed = time.time() - loop_start
                if elapsed < 0.05:
                    time.sleep(0.05 - elapsed)
                step += 1

    except Exception as e:
        print(f"[Trainer] Ended: {e}")

    try:
        cv2.destroyAllWindows()
    except Exception:
        pass

    create_backup_of_weights()
    np.save(WEIGHTS_PATH, weights)
    print(f"\nSaved imitation weights ({step} frames processed).")


if __name__ == '__main__':
    run_trainer()
