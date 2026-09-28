import time
from collections import deque

import numpy as np
import mss
import cv2

from fly_jjs.core.config import ConfigManager
from fly_jjs.core.learning import FlyLearner
from fly_jjs.core.rl import (ACTION_NAMES, NUM_ACTIONS, STOP_KEY, FlyBody, RewardSystem, countdown,
                             detect_monitor, draw_panel, get_brain_components)
from fly_jjs.core.storage import WEIGHTS_PATH, create_backup_of_weights
from fly_jjs.core.telemetry import TelemetryPublisher
from fly_jjs.core.vision import FlyEyes, detect_motion, detect_opponent

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
FRAME_SECONDS = 0.05
IDLE_PAUSE_SECONDS = 5.0   # no input for this long (menus, AFK): stop learning until you play


def run_trainer():
    cfg = ConfigManager.load_config()
    res_mode = cfg.get("resolution", "64x48")
    use_color = cfg.get("use_color", True)
    brain_steps = cfg.get("brain_steps", 2)

    print("\n" + "=" * 65)
    print("  FLY BRAIN IMITATION TRAINER (SUPERVISED LEARNING)")
    print("  ⚠️ IMPORTANT USER GUIDANCE:")
    print("  1. RESIZE ROBLOX WINDOW TO THE SMALLEST POSSIBLE SIZE.")
    print("  2. RECOMMEND AT LEAST 20+ MINUTES OF TRAINING DATA FOR GOOD RESULTS.")
    print(f"  Visual Mode: {res_mode} | Color: {use_color}")
    print("  Learning pauses while you don't touch the keyboard or mouse.")
    print("=" * 65)

    components = get_brain_components()
    monitor = detect_monitor()
    eyes = FlyEyes(components.brain, res_mode, use_color, frame_aspect=monitor["width"] / monitor["height"])
    print(f"[Vision] {eyes.num_neurons} visual neurons across both eyes")
    body = FlyBody(components, eyes, steps=brain_steps)

    learner = FlyLearner(len(components.dns), NUM_ACTIONS)
    learner.load(WEIGHTS_PATH)
    create_backup_of_weights()
    reward_sys = RewardSystem()
    publisher = TelemetryPublisher("train")

    active_keys = set()
    last_input = [time.time()]

    try:
        from pynput import keyboard, mouse

        def on_key_press(key):
            try:
                k = key.char.lower() if hasattr(key, 'char') and key.char else None
                if k in KEY_MAP:
                    active_keys.add(k)
                last_input[0] = time.time()
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
            last_input[0] = time.time()
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

    window = "Fly Trainer"
    start_time = time.time()
    last_save_time = time.time()
    prev_gray = None
    prev_actions = set()
    match = 0.5            # running average of how well the fly predicts your key presses
    trained_seconds = 0.0
    fps = 0.0
    step = 0
    events_log = deque(maxlen=8)

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

                rates = body.step(img, opp, threat)
                innate, pop_rates = body.innate_drive(rates)

                user_actions = np.zeros(NUM_ACTIONS, dtype=np.float32)
                for k in list(active_keys):
                    if k in KEY_MAP:
                        user_actions[KEY_MAP[k]] = 1.0
                    elif k == "click":
                        user_actions[MELEE_IDX] = 1.0
                pressed = {ACTION_NAMES[i] for i in np.flatnonzero(user_actions)}

                reward, events = reward_sys.compute(threat, motion, prev_actions, img)
                events_log.extend(f"{step}: {e}" for e in events)
                prev_actions = pressed

                learning = time.time() - last_input[0] < IDLE_PAUSE_SECONDS
                if learning:
                    # Every frame counts, including the ones where you press nothing: that
                    # is how the fly learns when *not* to attack.
                    probs = learner.imitate(rates, user_actions, reward=reward, innate=innate)
                    agreement = float(np.mean(user_actions * probs + (1 - user_actions) * (1 - probs)))
                    match = 0.995 * match + 0.005 * agreement
                    trained_seconds += FRAME_SECONDS
                else:
                    probs = learner.policy(rates, innate)

                trained_min = trained_seconds / 60.0
                progress_pct = min(100.0, (trained_min / 20.0) * 100.0)

                lines = [
                    (f"Step: {step} | Active Keys: {len(active_keys)} | FPS: {fps:4.1f}", (255, 255, 255)),
                    (f"Training time: {trained_min:.1f} / 20.0 mins ({progress_pct:.0f}%)", (0, 255, 0)),
                    (f"Fly predicts your keys: {match * 100:.0f}% match", (0, 200, 255)),
                    ("LEARNING" if learning else "PAUSED: waiting for you to play", (0, 255, 128) if learning else (255, 180, 0)),
                    ("Press ESC here to stop & save", (200, 200, 200)),
                ]
                cv2.imshow(window, draw_panel("FLY IMITATION TRAINER", lines, color=(255, 255, 0)))
                if cv2.waitKey(1) & 0xFF == STOP_KEY:
                    break

                publisher.publish({
                    "step": step, "fps": fps, "resolution": res_mode,
                    "dn_active_pct": float(np.mean(rates > 0.05) * 100), "fired": body.fired,
                    "dopamine": 0.0, "value": learner.value, "reward": reward,
                    "avg_reward": learner.avg_reward(), "total_reward": learner.total_reward,
                    "actions": {n: float(p) for n, p in zip(ACTION_NAMES, probs)},
                    "pressed": sorted(pressed),
                    "innate": {n: float(r) for n, r in zip(ACTION_NAMES, pop_rates)},
                    "vision": {c: float(v) for c, v in eyes.last_drive.items()},
                    "eye_neurons": eyes.num_neurons,
                    "opponent": {"dx": int(opp[0]), "size": int(opp[2]), "threat": float(threat)},
                    "hits": {"landed": reward_sys.total_hits_landed, "taken": reward_sys.total_hits_taken,
                             "kills": reward_sys.total_kills},
                    "events": list(events_log) + [f"imitation match {match * 100:.0f}%"],
                })

                if time.time() - last_save_time > 30:
                    learner.save(WEIGHTS_PATH)
                    last_save_time = time.time()

                elapsed = time.time() - loop_start
                if elapsed < FRAME_SECONDS:
                    time.sleep(FRAME_SECONDS - elapsed)
                fps = 0.9 * fps + 0.1 / max(time.time() - loop_start, 1e-3)
                step += 1

    except KeyboardInterrupt:
        print("\n[Trainer] Stopped by user.")
    except Exception as e:
        print(f"[Trainer] Ended: {e}")
    finally:
        publisher.close()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

    learner.save(WEIGHTS_PATH)
    print(f"\nSaved imitation weights ({step} frames processed, "
          f"{(time.time() - start_time) / 60:.1f} min session).")


if __name__ == '__main__':
    run_trainer()
