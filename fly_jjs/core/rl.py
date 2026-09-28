"""Play and Manual Reward mode: the fly plays the real game and learns from it."""
import time
import threading
from collections import deque

import numpy as np
import mss
import cv2

from fly_jjs.core.actions import ACTION_NAMES, NUM_ACTIONS  # noqa: F401
from fly_jjs.core.agent import FlyAgent
from fly_jjs.core.brain import FlyBody, get_brain_components  # noqa: F401
from fly_jjs.core.combat import PatternRecognizer, RewardSystem  # noqa: F401
from fly_jjs.core.config import ConfigManager
from fly_jjs.core.controls import make_backend
from fly_jjs.core.learning import FlyLearner  # noqa: F401
from fly_jjs.core.screen import detect_monitor
from fly_jjs.core.storage import WEIGHTS_PATH, create_backup_of_weights
from fly_jjs.core.telemetry import TelemetryPublisher
from fly_jjs.core.vision import detect_motion, detect_opponent, get_pixel_grids  # noqa: F401

MANUAL_REWARD = 1.5
FRAME_SECONDS = 0.05    # 20 game frames per second
STOP_KEY = 27           # ESC. Not Q: the fly presses Q itself to dash.


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


def snapshot(step, agent, fps, res_mode, events_log):
    """Telemetry for the [L] live monitor."""
    body, learner, rewards, opp = agent.body, agent.learner, agent.rewards, step.opponent
    return {
        "step": int(learner.updates + learner.imitation_updates), "fps": fps, "resolution": res_mode,
        "dn_active_pct": float(np.mean(step.rates[:body.num_dns] > 0.05) * 100),
        "readout_neurons": int(body.num_inputs),
        "readout_active_pct": float(np.mean(step.rates > 0.05) * 100),
        "fired": body.fired,
        "dopamine": learner.dopamine, "value": learner.value, "reward": step.reward,
        "avg_reward": learner.avg_reward(), "total_reward": learner.total_reward,
        "actions": {n: float(p) for n, p in zip(ACTION_NAMES, step.probs)},
        "pressed": sorted(step.actions),
        "innate": {n: float(r) for n, r in zip(ACTION_NAMES, step.pop_rates)},
        "vision": {c: float(v) for c, v in agent.eyes.last_drive.items()},
        "eye_neurons": agent.eyes.num_neurons,
        "opponent": {"dx": int(opp.dx), "size": int(opp.size) if opp.visible else 0,
                     "threat": float(opp.threat), "distance": float(opp.distance), "attack": float(opp.attack)},
        "pattern_burst": bool(step.pattern_burst),
        "hits": {"landed": rewards.total_hits_landed, "taken": rewards.total_hits_taken,
                 "kills": rewards.total_kills},
        "events": list(events_log),
    }


def run_rl(manual_mode=False):
    cfg = ConfigManager.load_config()
    res_mode = cfg.get("resolution", "64x48")

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
    print("  2. TURN ON SHIFT LOCK in Roblox so the fly can turn the camera.")
    print("  3. RECOMMEND AT LEAST 20+ MINUTES OF TRAINING DATA FOR GOOD RESULTS.")
    print(f"  Visual Mode: {res_mode} | Color: {cfg.get('use_color', True)} | "
          f"Target Lock: {cfg.get('camera_lock_enabled', True)} | Brain steps/frame: {cfg.get('brain_steps', 2)}")
    print("  To stop: press ESC in the 'Fly Brain RL' window, or move the mouse")
    print("  to the top-left corner of the screen.")
    print("=" * 65)

    components = get_brain_components()
    monitor = detect_monitor()
    agent = FlyAgent(components, cfg, monitor["width"], monitor["height"], make_backend())
    print(f"[Vision] {agent.eyes.num_neurons} visual neurons across both eyes; "
          f"the fly reads {agent.body.num_inputs:,} neurons")
    agent.learner.load(WEIGHTS_PATH)
    create_backup_of_weights()
    manual = ManualRewards() if manual_mode else None
    publisher = TelemetryPublisher("manual" if manual_mode else "play")
    window = "Fly Brain RL"
    dash = None
    if cfg.get("dashboard"):
        from fly_jjs.core.dashboard import DEFAULT_PORT, BrainDashboard
        dash = BrainDashboard(components.brain, port=cfg.get("dashboard_port", DEFAULT_PORT)).attach(agent.body)
        dash.start()

    events_log = deque(maxlen=8)
    last_save_time = time.time()
    fps = 0.0
    frames = 0

    try:
        countdown(window)
        with mss.mss() as sct:
            while True:
                loop_start = time.time()
                img = np.array(sct.grab(monitor))
                manual_reward = manual.take() if manual is not None else 0.0
                step = agent.step(img, loop_start, manual_reward)
                events_log.extend(f"{frames}: {e}" for e in step.events)

                opp = step.opponent
                seen = (f"opponent {'close' if opp.distance < 0.35 else 'mid' if opp.distance < 0.7 else 'far'}"
                        f", attack {opp.attack:.1f}") if opp.visible else "searching for opponent"
                lines = [
                    (f"Frame: {frames} | Res: {res_mode} | FPS: {fps:4.1f}", (255, 255, 255)),
                    (f"Dopamine (surprise): {agent.learner.dopamine:+.2f}", (0, 200, 255)),
                    (f"Expected reward: {agent.learner.value:+.2f} | Avg: {agent.learner.avg_reward():+.3f}",
                     (200, 200, 255)),
                    (f"Pressing: {', '.join(sorted(step.actions)) or '-'}", (0, 255, 128)),
                    (f"Vision: {seen}", (255, 255, 0)),
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

                publisher.publish(snapshot(step, agent, fps, res_mode, events_log))
                if dash is not None and frames % 4 == 0:
                    dash.show_eye(img)
                    rw = agent.rewards
                    dash.publish(mode="manual" if manual_mode else "play", title="Playing Jujutsu Shenanigans",
                                 actions=sorted(step.actions), log=list(events_log)[-4:][::-1],
                                 fight={"left": {"name": "Fly", "value": round(100 * rw.our_health), "max": 100},
                                        "right": {"name": "Opponent", "value": round(100 * rw.enemy_health),
                                                  "max": 100},
                                        "label": "Read from the health bars on screen",
                                        "clock": f"frame {frames}",
                                        "record": {"what": "Knockouts", "left": rw.total_kills,
                                                   "right": rw.total_deaths}})

                if time.time() - last_save_time > 60:
                    agent.learner.save(WEIGHTS_PATH)
                    last_save_time = time.time()

                elapsed = time.time() - loop_start
                if elapsed < FRAME_SECONDS:
                    time.sleep(FRAME_SECONDS - elapsed)
                fps = 0.9 * fps + 0.1 / max(time.time() - loop_start, 1e-3)
                frames += 1
    except KeyboardInterrupt:
        print("\n[RL] Stopped by user.")
    except Exception as e:
        print(f"[RL] Loop ended: {e}")
    finally:
        agent.release()          # never leave W (or anything) held down
        if manual is not None:
            manual.stop()
        if dash is not None:
            dash.stop()
        publisher.close()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

    agent.learner.save(WEIGHTS_PATH)
    print(f"\nSession ended after {frames} brain cycles.")


if __name__ == '__main__':
    run_rl()
