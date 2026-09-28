import time
from collections import deque

import numpy as np
import mss
import cv2

from fly_jjs.core.actions import ACTION_INDEX, NUM_ACTIONS
from fly_jjs.core.agent import FlyAgent
from fly_jjs.core.brain import get_brain_components
from fly_jjs.core.config import ConfigManager
from fly_jjs.core.controls import RecordingBackend
from fly_jjs.core.rl import STOP_KEY, countdown, draw_panel, snapshot
from fly_jjs.core.screen import detect_monitor
from fly_jjs.core.storage import WEIGHTS_PATH, create_backup_of_weights
from fly_jjs.core.telemetry import TelemetryPublisher

KEY_MAP = {
    'w': ACTION_INDEX["forward"],
    'a': ACTION_INDEX["left"],
    's': ACTION_INDEX["back"],
    'd': ACTION_INDEX["right"],
    '1': ACTION_INDEX["skill1"],
    '2': ACTION_INDEX["skill2"],
    '3': ACTION_INDEX["skill3"],
    '4': ACTION_INDEX["skill4"],
    'q': ACTION_INDEX["dash"],
    'f': ACTION_INDEX["block"],
    'r': ACTION_INDEX["special"],
    'g': ACTION_INDEX["awaken"],
    'space': ACTION_INDEX["jump"],
}
MELEE_IDX = ACTION_INDEX["melee"]
SPRINT_IDX = ACTION_INDEX["sprint"]
DOUBLE_TAP = 0.35          # seconds: W pressed twice this fast, then held, is a sprint
FRAME_SECONDS = 0.05
IDLE_PAUSE_SECONDS = 5.0   # no input for this long (menus, AFK): stop learning until you play


class PlayerInput:
    """What the player is holding right now, from global keyboard/mouse listeners."""

    def __init__(self):
        self.active = set()
        self.last_input = time.time()
        self.sprinting = False
        self._last_w = -9.0
        self.listening = False

    def press(self, k, now=None):
        now = time.time() if now is None else now
        self.last_input = now
        if k == 'w' and 'w' not in self.active:
            self.sprinting = now - self._last_w < DOUBLE_TAP
            self._last_w = now
        if k in KEY_MAP or k == "click":
            self.active.add(k)

    def release(self, k):
        self.active.discard(k)
        if k == 'w':
            self.sprinting = False

    def mask(self):
        m = np.zeros(NUM_ACTIONS, dtype=np.float32)
        for k in self.active:
            if k in KEY_MAP:
                m[KEY_MAP[k]] = 1.0
            elif k == "click":
                m[MELEE_IDX] = 1.0
        if self.sprinting and 'w' in self.active:
            m[SPRINT_IDX] = 1.0
        return m

    def start(self):
        try:
            from pynput import keyboard, mouse

            def name(key):
                if key == keyboard.Key.space:
                    return 'space'
                char = getattr(key, 'char', None)
                return char.lower() if char else None

            def on_key_press(key):
                k = name(key)
                if k:
                    self.press(k)
                else:
                    self.last_input = time.time()

            def on_key_release(key):
                k = name(key)
                if k:
                    self.release(k)

            def on_click(x, y, button, pressed):
                if button == mouse.Button.left:
                    if pressed:
                        self.press("click")
                    else:
                        self.release("click")
                else:
                    self.last_input = time.time()

            keyboard.Listener(on_press=on_key_press, on_release=on_key_release, daemon=True).start()
            mouse.Listener(on_click=on_click, daemon=True).start()
            self.listening = True
            print("[Trainer] Input listeners activated. Play Roblox now!")
        except Exception as e:
            print(f"[Trainer] Listener warning: {e}. Running in simulation mode.")


def run_trainer():
    cfg = ConfigManager.load_config()
    res_mode = cfg.get("resolution", "64x48")

    print("\n" + "=" * 65)
    print("  FLY BRAIN IMITATION TRAINER (SUPERVISED LEARNING)")
    print("  ⚠️ IMPORTANT USER GUIDANCE:")
    print("  1. RESIZE ROBLOX WINDOW TO THE SMALLEST POSSIBLE SIZE.")
    print("  2. RECOMMEND AT LEAST 20+ MINUTES OF TRAINING DATA FOR GOOD RESULTS.")
    print(f"  Visual Mode: {res_mode} | Color: {cfg.get('use_color', True)} | "
          f"Brain steps/frame: {cfg.get('brain_steps', 2)}")
    print("  Learning pauses while you don't touch the keyboard or mouse.")
    print("=" * 65)

    components = get_brain_components()
    monitor = detect_monitor()
    # The fly only watches: nothing is sent to the game.
    agent = FlyAgent(components, cfg, monitor["width"], monitor["height"], RecordingBackend())
    print(f"[Vision] {agent.eyes.num_neurons} visual neurons; the fly reads {agent.body.num_inputs:,} neurons")
    agent.learner.load(WEIGHTS_PATH)
    create_backup_of_weights()
    publisher = TelemetryPublisher("train")
    player = PlayerInput()
    player.start()

    window = "Fly Trainer"
    start_time = time.time()
    last_save_time = time.time()
    match = 0.5            # running average of how well the fly predicts your key presses
    trained_seconds = 0.0
    fps = 0.0
    frames = 0
    events_log = deque(maxlen=8)

    try:
        countdown(window)
        with mss.mss() as sct:
            while True:
                loop_start = time.time()
                img = np.array(sct.grab(monitor))
                target = player.mask()
                learning = time.time() - player.last_input < IDLE_PAUSE_SECONDS
                # Every frame counts, including the ones where you press nothing: that is
                # how the fly learns when *not* to attack.
                step = agent.watch(img, loop_start, target, learn=learning)
                events_log.extend(f"{frames}: {e}" for e in step.events)
                if learning:
                    agreement = float(np.mean(target * step.probs + (1 - target) * (1 - step.probs)))
                    match = 0.995 * match + 0.005 * agreement
                    trained_seconds += FRAME_SECONDS

                trained_min = trained_seconds / 60.0
                progress_pct = min(100.0, (trained_min / 20.0) * 100.0)
                lines = [
                    (f"Frame: {frames} | Keys held: {len(player.active)} | FPS: {fps:4.1f}", (255, 255, 255)),
                    (f"Training time: {trained_min:.1f} / 20.0 mins ({progress_pct:.0f}%)", (0, 255, 0)),
                    (f"Fly predicts your keys: {match * 100:.0f}% match", (0, 200, 255)),
                    ("LEARNING" if learning else "PAUSED: waiting for you to play",
                     (0, 255, 128) if learning else (255, 180, 0)),
                    ("Press ESC here to stop & save", (200, 200, 200)),
                ]
                cv2.imshow(window, draw_panel("FLY IMITATION TRAINER", lines, color=(255, 255, 0)))
                if cv2.waitKey(1) & 0xFF == STOP_KEY:
                    break

                snap = snapshot(step, agent, fps, res_mode, events_log)
                snap["events"] = snap["events"] + [f"imitation match {match * 100:.0f}%"]
                publisher.publish(snap)

                if time.time() - last_save_time > 30:
                    agent.learner.save(WEIGHTS_PATH)
                    last_save_time = time.time()

                elapsed = time.time() - loop_start
                if elapsed < FRAME_SECONDS:
                    time.sleep(FRAME_SECONDS - elapsed)
                fps = 0.9 * fps + 0.1 / max(time.time() - loop_start, 1e-3)
                frames += 1

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

    agent.learner.save(WEIGHTS_PATH)
    print(f"\nSaved imitation weights ({frames} frames processed, "
          f"{(time.time() - start_time) / 60:.1f} min session).")


if __name__ == '__main__':
    run_trainer()
