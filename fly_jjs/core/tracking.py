"""Finding and following the opponent on screen.

detect_opponent() looks at one frame at a time for the biggest bright blob, so it loses
anyone who isn't brightly dressed and knows nothing about approach or attacks.
OpponentTracker follows one target over time:

* Candidates come from three cues: motion after cancelling the camera's own turning
  (phase correlation, like the fly separating self-motion from object motion),
  brightness, and colour saturation. A standing, colourful avatar and a moving dark
  one are both found.
* The candidate that best fits the track (near where the opponent should be, near the
  screen centre the camera keeps it at) wins, and the track coasts briefly through
  missed frames.
* It estimates distance from apparent size, looming speed, and an "attack" cue: a
  sudden burst of motion or glow around the opponent (a wind-up or a VFX).
"""
from typing import NamedTuple

import numpy as np
import cv2

WORK_WIDTH = 160          # tracking runs on a small copy of the frame
MIN_AREA = 10             # candidate blobs smaller than this (work pixels) are ignored
COAST_SECONDS = 0.4       # keep reporting a lost opponent this long
BAND = (0.12, 0.88)       # rows of the screen searched (keeps clear of HUD bars)
# Where your own character stands in a third-person view (x0, y0, x1, y1 as fractions
# of the window). Blobs sitting inside it are you, not the opponent.
SELF_ZONE = (0.30, 0.55, 0.52, 0.90)
# Apparent height of an opponent (fraction of window height) at melee range and far away.
NEAR_HEIGHT, FAR_HEIGHT = 0.20, 0.06


class Opponent(NamedTuple):
    visible: bool
    dx: float = 0.0        # pixels right of the screen centre
    dy: float = 0.0        # pixels below the screen centre
    size: float = 0.0      # sqrt(area) in screen pixels
    distance: float = 1.0  # 0 = melee range ... 1 = far away / unknown
    loom: float = 0.0      # growth of apparent size per second (relative); > 0 approaching
    attack: float = 0.0    # 0..1: sudden motion or glow on the opponent (an attack coming)
    threat: float = 0.0    # 0..1: how close and aggressive the opponent looks
    seen_ago: float = 99.0 # seconds since the last real detection

    def as_legacy(self):
        """((dx, dy, size), threat) like detect_opponent, with size 0 when not visible."""
        if not self.visible:
            return (0, 0, 0), 0.0
        return (int(self.dx), int(self.dy), int(self.size)), float(self.threat)


NOBODY = Opponent(False)


class OpponentTracker:
    def __init__(self, width, height, self_zone=SELF_ZONE, near_height=NEAR_HEIGHT, far_height=FAR_HEIGHT,
                 ignore=()):
        """`ignore`: screen regions (x0, y0, x1, y1 fractions) never searched, e.g. health bars."""
        self.width, self.height = width, height
        self.self_zone = self_zone
        self.ignore = [tuple(r) for r in ignore]
        self.near_height, self.far_height = near_height, far_height
        self.body_height = 0.0    # bounding-box height, work pixels
        self.scale = WORK_WIDTH / float(width)
        self.work_size = (WORK_WIDTH, max(8, int(round(height * self.scale))))
        self.window = cv2.createHanningWindow(self.work_size, cv2.CV_32F)
        self.prev = None
        self.pos = None           # (x, y) in work pixels
        self.vel = np.zeros(2)    # work pixels per second
        self.size = 0.0           # sqrt(area), work pixels
        self.loom = 0.0
        self.attack = 0.0
        self.energy_baseline = None
        self.last_time = None
        self.seen_ago = 99.0
        self.camera_shift = (0.0, 0.0)
        self.scene_motion = 0.0   # mean change between frames with the camera's turning removed (0..1)

    def reset(self):
        self.__init__(self.width, self.height, self.self_zone, self.near_height, self.far_height, self.ignore)

    def _masks(self, small, bgr_small):
        h = small.shape[0]
        motion = np.zeros_like(small)
        if self.prev is not None:
            (sx, sy), _ = cv2.phaseCorrelate(self.prev.astype(np.float32), small.astype(np.float32), self.window)
            self.camera_shift = (sx, sy)
            aligned = cv2.warpAffine(self.prev, np.float32([[1, 0, sx], [0, 1, sy]]), self.work_size,
                                     borderMode=cv2.BORDER_REPLICATE)
            motion = cv2.absdiff(small, aligned)
        self.scene_motion = float(motion.mean()) / 255.0
        moving = (motion > 20).astype(np.uint8)
        bright = (small > 180).astype(np.uint8)
        hsv = cv2.cvtColor(bgr_small, cv2.COLOR_BGR2HSV)
        colourful = ((hsv[:, :, 1] > 140) & (hsv[:, :, 2] > 70)).astype(np.uint8)
        top, bottom = int(BAND[0] * h), int(BAND[1] * h)
        w = small.shape[1]
        # Your own character: when the camera turns it stays put on screen while the world
        # slides, so after cancelling the turn it leaves a "ghost" as wide as the turn.
        zx0, zy0, zx1, zy1 = self.self_zone
        ghost = int(abs(self.camera_shift[0])) + 1
        for m in (moving, bright, colourful):
            m[:top] = 0
            m[bottom:] = 0
            pad = ghost if m is moving else 0
            m[int(zy0 * h):int(zy1 * h) + 1, max(0, int(zx0 * w) - pad):int(zx1 * w) + 1 + pad] = 0
            for x0, y0, x1, y1 in self.ignore:   # HUD: a red health bar is not an opponent
                m[max(0, int((y0 - 0.03) * h)):int((y1 + 0.03) * h) + 1,
                  max(0, int((x0 - 0.03) * w)):int((x1 + 0.03) * w) + 1] = 0
        return motion, moving, bright, colourful

    def update(self, img, now):
        """Track the opponent in this BGRA/BGR frame. `now` is the frame time in seconds."""
        dt = 0.05 if self.last_time is None else max(1e-3, now - self.last_time)
        self.last_time = now
        bgr_small = cv2.resize(img[:, :, :3], self.work_size, interpolation=cv2.INTER_AREA)
        small = cv2.cvtColor(bgr_small, cv2.COLOR_BGR2GRAY)
        motion, moving, bright, colourful = self._masks(small, bgr_small)
        self.prev = small

        mask = cv2.morphologyEx(moving | bright | colourful, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)

        w, h = self.work_size
        if self.pos is not None:
            predicted = np.array(self.pos) + self.vel * dt
        else:
            predicted = None
        best, best_score = None, 0.0
        for i in range(1, count):
            x, y, bw, bh, area = stats[i]
            if area < MIN_AREA or area > 0.4 * w * h:
                continue
            region = labels[y:y + bh, x:x + bw] == i
            move_frac = float(moving[y:y + bh, x:x + bw][region].mean())
            glow_frac = float((bright | colourful)[y:y + bh, x:x + bw][region].mean())
            cx, cy = centroids[i]
            score = np.sqrt(area) * (0.4 + move_frac) * (0.4 + glow_frac)
            score *= 1.0 - 0.35 * abs(cx - w / 2) / (w / 2)                 # the camera keeps it centred
            if predicted is not None and self.seen_ago < COAST_SECONDS * 3:
                gap = np.hypot(cx - predicted[0], cy - predicted[1]) / w
                score *= np.exp(-(gap / 0.25) ** 2) * 1.5 + 0.2             # stick with the track
            if score > best_score:
                best, best_score = (cx, cy, np.sqrt(area), (x, y, bw, bh)), score

        if best is not None and best_score > 1.0:
            cx, cy, size, box = best
            box_h = float(box[3])
            if self.pos is None or self.seen_ago > COAST_SECONDS * 3:
                self.pos, self.vel, self.size, self.loom = (cx, cy), np.zeros(2), size, 0.0
                self.body_height = box_h
            else:
                new_vel = (np.array([cx, cy]) - np.array(self.pos)) / dt
                self.vel = 0.6 * self.vel + 0.4 * new_vel
                self.pos = (0.35 * self.pos[0] + 0.65 * cx, 0.35 * self.pos[1] + 0.65 * cy)
                growth = (size - self.size) / max(self.size, 1.0) / dt
                self.loom = 0.7 * self.loom + 0.3 * growth
                self.size = 0.7 * self.size + 0.3 * size
                self.body_height = 0.7 * self.body_height + 0.3 * box_h
            self.seen_ago = 0.0
            self._update_attack(motion, box)
        else:
            self.seen_ago += dt
            if self.pos is not None and self.seen_ago < COAST_SECONDS:
                self.pos = (self.pos[0] + self.vel[0] * dt, self.pos[1] + self.vel[1] * dt)
                self.vel *= 0.8
            self.attack *= 0.8
            self.loom *= 0.8

        if self.pos is None or self.seen_ago >= COAST_SECONDS:
            return NOBODY._replace(seen_ago=self.seen_ago)
        size_px = self.size / self.scale
        dx = (self.pos[0] - w / 2) / self.scale
        dy = (self.pos[1] - h / 2) / self.scale
        tall = max(self.body_height / h, 1e-3)
        distance = float(np.clip(np.log(self.near_height / tall) / np.log(self.near_height / self.far_height),
                                 0.0, 1.0))
        threat = float(np.clip(max(1.0 - distance, self.attack), 0.0, 1.0))
        return Opponent(True, float(dx), float(dy), float(size_px), distance,
                        float(np.clip(self.loom, -5, 5)), float(self.attack), threat, self.seen_ago)

    def _update_attack(self, motion, box):
        """Sudden motion energy around the opponent compared with its own recent baseline."""
        x, y, bw, bh = box
        pad_x, pad_y = bw // 2 + 2, bh // 2 + 2
        region = motion[max(0, y - pad_y):y + bh + pad_y, max(0, x - pad_x):x + bw + pad_x]
        energy = float(region.mean()) / 255.0 if region.size else 0.0
        if self.energy_baseline is None:
            self.energy_baseline = energy
        surprise = (energy - self.energy_baseline) / 0.08
        self.energy_baseline = 0.95 * self.energy_baseline + 0.05 * energy
        level = float(np.clip(surprise, 0.0, 1.0))
        self.attack = level if level > self.attack else 0.85 * self.attack + 0.15 * level
