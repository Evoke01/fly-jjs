"""Turning the fly's decisions into keyboard and mouse input.

The old loop tapped every key for a single frame, so W/A/S/D barely moved the
character and F never held a block. InputController keeps keys in the right state:

* Movement (W/A/S/D) and block (F) are held down while the fly wants them.
* Melee clicks at a combo rhythm while the fly wants to attack.
* Skills, dash, special, awaken and jump are tapped when the fly switches them on.
* Sprint double-taps W, then keeps W held.
* The camera turns toward the tracked opponent with a damped (PD) controller and
  sweeps to search when nobody has been in view for a while.

Backends do the actual input: DirectInputBackend for the real game (pydirectinput,
Windows), RecordingBackend for tests, and the arena's own backend for simulation.
"""
import time

import numpy as np

from fly_jjs.core.actions import HELD_KEYS, OPPOSITES, TAPPED_KEYS

MELEE_INTERVAL = 0.14    # seconds between M1 clicks while attacking
RETAP_INTERVAL = 0.35    # a tapped action switched on again this soon is not re-pressed
SPRINT_GAP = 0.05        # seconds between the two W taps of a sprint
SEARCH_AFTER = 1.2       # seconds without an opponent before the camera starts sweeping


class RecordingBackend:
    """Remembers every input event instead of sending it (tests, dry runs)."""

    sprint_gap = 0.0

    def __init__(self):
        self.events = []
        self.held = set()

    def key_down(self, key):
        self.held.add(key)
        self.events.append(("down", key))

    def key_up(self, key):
        self.held.discard(key)
        self.events.append(("up", key))

    def tap(self, key):
        self.events.append(("tap", key))

    def click(self):
        self.events.append(("click", None))

    def move(self, dx, dy):
        self.events.append(("move", (int(dx), int(dy))))

    def camera_button(self, down):
        self.events.append(("rmb", down))


class DirectInputBackend:
    """Real keyboard and mouse through pydirectinput (Windows)."""

    sprint_gap = SPRINT_GAP   # the game has to see two separate W presses

    def __init__(self):
        import pydirectinput
        pydirectinput.FAILSAFE = True
        self.pdi = pydirectinput

    def key_down(self, key):
        self.pdi.keyDown(key, _pause=False)

    def key_up(self, key):
        self.pdi.keyUp(key, _pause=False)

    def tap(self, key):
        self.pdi.press(key, _pause=False)

    def click(self):
        # At the current cursor position: moving the cursor would fight the camera.
        self.pdi.click(_pause=False)

    def move(self, dx, dy):
        self.pdi.moveRel(int(dx), int(dy), relative=True, _pause=False)

    def camera_button(self, down):
        if down:
            self.pdi.mouseDown(button="right", _pause=False)
        else:
            self.pdi.mouseUp(button="right", _pause=False)


def make_backend():
    """DirectInputBackend if pydirectinput works here, else a RecordingBackend (dry run)."""
    try:
        return DirectInputBackend()
    except Exception as e:
        print(f"[Controls] pydirectinput unavailable ({e}); running without sending input.")
        return RecordingBackend()


class CameraController:
    """Damped tracking of the opponent's screen position, plus a search sweep."""

    def __init__(self, backend, width, height, sensitivity=0.3, damping=0.5, max_step=80,
                 dead_zone=0.03, search_speed=30, hold_right_button=False):
        self.backend = backend
        self.width, self.height = width, height
        self.kp = sensitivity
        self.kd = sensitivity * damping
        self.max_step = max_step
        self.dead_zone = dead_zone * width
        self.search_speed = search_speed
        self.hold_right_button = hold_right_button
        self.reset()

    def reset(self):
        self.prev_error = None
        self.last_seen = None     # set on the first update, in whatever clock the caller uses

    def update(self, target, now=None):
        """`target` is (dx, dy) of the opponent from the screen centre in pixels, or None.
        Returns the (dx, dy) mouse movement sent."""
        now = time.time() if now is None else now
        if self.last_seen is None:
            self.last_seen = now
        if target is None:
            self.prev_error = None
            if now - self.last_seen < SEARCH_AFTER:
                return 0, 0
            move = (self.search_speed, 0)
        else:
            self.last_seen = now
            ex, ey = float(target[0]), float(target[1]) * 0.5   # keep pitch changes gentle
            if abs(ex) < self.dead_zone and abs(ey) < self.dead_zone:
                self.prev_error = (ex, ey)
                return 0, 0
            px, py = self.prev_error if self.prev_error is not None else (ex, ey)
            mx = self.kp * ex + self.kd * (ex - px)
            my = self.kp * ey + self.kd * (ey - py)
            self.prev_error = (ex, ey)
            move = (float(np.clip(mx, -self.max_step, self.max_step)),
                    float(np.clip(my, -self.max_step / 2, self.max_step / 2)))
        if abs(move[0]) < 1 and abs(move[1]) < 1:
            return 0, 0
        if self.hold_right_button:
            self.backend.camera_button(True)
        self.backend.move(move[0], move[1])
        if self.hold_right_button:
            self.backend.camera_button(False)
        return int(move[0]), int(move[1])


class InputController:
    """Keeps held keys, clicks and taps in sync with the fly's chosen actions."""

    def __init__(self, backend):
        self.backend = backend
        self.held = set()               # keys currently held down by us
        self.reset()

    def reset(self):
        """Forget timing (a new fight, or a clock that starts over)."""
        self.active = set()             # actions that were on last frame
        self.last_tap = {}              # action -> time of its last tap
        self.last_click = None

    def _since(self, then, now):
        # A clock that went backwards (a new arena fight) counts as "long ago".
        return float("inf") if then is None or now < then else now - then

    def apply(self, actions, now=None):
        """Bring the keyboard/mouse in line with this frame's set of action names."""
        now = time.time() if now is None else now
        actions = set(actions)
        for a, b in OPPOSITES:
            # W+S or A+D cancel out in the game: keep whichever was already going, else neither.
            if a in actions and b in actions:
                keep = a if a in self.active else b if b in self.active else None
                actions -= {a, b}
                if keep:
                    actions.add(keep)
        want_held = {HELD_KEYS[a] for a in actions if a in HELD_KEYS}
        sprint_start = "sprint" in actions and "sprint" not in self.active
        if "sprint" in actions:
            want_held.add("w")

        for key in sorted(self.held - want_held):
            self.backend.key_up(key)
        if sprint_start:
            # Double-tap W, then keep holding it.
            if "w" in self.held:
                self.backend.key_up("w")
                self.held.discard("w")
            self.backend.tap("w")
            gap = getattr(self.backend, "sprint_gap", 0.0)
            if gap:
                time.sleep(gap)
        for key in sorted(want_held - self.held):
            self.backend.key_down(key)
        self.held = want_held

        if "melee" in actions and "block" not in actions and self._since(self.last_click, now) >= MELEE_INTERVAL:
            self.backend.click()
            self.last_click = now

        for action, key in TAPPED_KEYS.items():
            if action in actions and action not in self.active:
                if self._since(self.last_tap.get(action), now) >= RETAP_INTERVAL:
                    self.backend.tap(key)
                    self.last_tap[action] = now
        self.active = actions
        return actions

    def release_all(self):
        for key in sorted(self.held):
            self.backend.key_up(key)
        self.held = set()
        self.active = set()
