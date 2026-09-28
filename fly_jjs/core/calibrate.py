"""[C] Calibrate: show the fly where the health bars and your own character are.

The fly's rewards come from reading health bars off the screen, and its opponent
tracker must know which figure is you. Game layouts differ with window size and
updates, so you draw boxes on a screenshot of your game once and they are saved to the
config. Everything else keeps working without calibration, using the defaults.
"""
import numpy as np
import cv2

from fly_jjs.core.combat import bar_colour, bar_fill
from fly_jjs.core.config import ConfigManager
from fly_jjs.core.screen import detect_monitor

STEPS = [
    ("self_bar", "YOUR health bar (while it is FULL)"),
    ("enemy_bar", "the OPPONENT's health bar, if your game shows one (C to skip)"),
    ("self_zone", "YOUR character (C to skip)"),
]


def _select(image, prompt):
    title = f"{prompt} - drag a box, then ENTER (C = skip)"
    try:
        x, y, w, h = cv2.selectROI(title, image, showCrosshair=False, fromCenter=False)
    finally:
        try:
            cv2.destroyWindow(title)
        except Exception:
            pass
    return None if w < 4 or h < 3 else (int(x), int(y), int(w), int(h))


def calibration_from_boxes(image, boxes):
    """Config values from pixel boxes {step: (x, y, w, h)} on a BGR screenshot."""
    H, W = image.shape[:2]
    out = {}
    bars = {}
    for key, name in (("self_bar", "self"), ("enemy_bar", "enemy")):
        box = boxes.get(key)
        if box:
            x, y, w, h = box
            bars[name] = {"roi": [x / W, y / H, (x + w) / W, (y + h) / H],
                          "color": bar_colour(image[y:y + h, x:x + w])}
    if bars:
        out["hp_bars"] = bars
    zone = boxes.get("self_zone")
    if zone:
        x, y, w, h = zone
        out["self_zone"] = [x / W, y / H, (x + w) / W, (y + h) / H]
    return out


def run_calibration():
    print("\n" + "=" * 65)
    print("  🎯 CALIBRATE HEALTH BARS & YOUR CHARACTER")
    print("  Open Roblox with a normal fight view, your health FULL.")
    print("  A screenshot will open: drag a tight box and press ENTER.")
    print("=" * 65)
    input("  Press Enter when the game is ready...")
    monitor = detect_monitor()
    try:
        import mss
        with mss.mss() as sct:
            image = np.array(sct.grab(monitor))[:, :, :3].copy()
    except Exception as e:
        print(f"  [!] Could not capture the screen: {e}")
        return False

    boxes = {}
    try:
        for key, prompt in STEPS:
            print(f"  → Select {prompt}")
            boxes[key] = _select(image, prompt)
    except cv2.error as e:
        print(f"  [!] This OpenCV build has no windows ({e}). Install opencv-python (not headless).")
        return False

    values = calibration_from_boxes(image, boxes)
    if not values:
        print("  Nothing selected; calibration unchanged.")
        return False
    cfg = ConfigManager.load_config()
    cfg.update(values)
    ConfigManager.save_config(cfg)

    for name, bar in values.get("hp_bars", {}).items():
        fill = bar_fill(image, bar["roi"], bar["color"])
        print(f"  ✓ {'Your' if name == 'self' else 'Opponent'} health bar saved, colour BGR {bar['color']}, "
              f"reads {fill * 100:.0f}% now")
    if "self_zone" in values:
        print("  ✓ Your character's position saved (the tracker will ignore it)")
    return True


def reset_calibration():
    cfg = ConfigManager.load_config()
    for key in ("hp_bars", "self_zone"):
        cfg.pop(key, None)
    ConfigManager.save_config(cfg)
