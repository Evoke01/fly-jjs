import unittest

import numpy as np

from fly_jjs.core.config import RESOLUTION_PRESETS
from fly_jjs.core.vision import CHANNEL_TYPES, COLOR_CHANNELS, MAX_DRIVE, FlyEyes, grid_for


class FakeBrain:
    """Stands in for flybrain.FlyBrain: every cell type has `per_side` neurons per side."""

    def __init__(self, per_side=60):
        self.per_side = per_side
        self.blocks = {}

    def cells(self, types, side=None):
        out = []
        for t in types:
            for s in ("L", "R"):
                if side and s != side:
                    continue
                if (t, s) not in self.blocks:
                    start = len(self.blocks) * self.per_side
                    self.blocks[(t, s)] = np.arange(start, start + self.per_side)
                out.append(self.blocks[(t, s)])
        return np.concatenate(out) if out else np.array([], dtype=np.int64)


def frame(w=320, h=240, blob=None, value=240, background=60):
    """BGRA frame, optionally with a bright square blob at (x, y) (its top-left corner)."""
    img = np.full((h, w, 4), background, dtype=np.uint8)
    img[:, :, 3] = 255
    if blob is not None:
        x, y = blob
        img[y:y + 30, x:x + 30, :3] = value
    return img


def driven(eyes, injections):
    """{neuron: drive} from an injection list; also checks each neuron appears once."""
    out = {}
    for idx, amount in injections:
        for n in np.atleast_1d(idx):
            assert int(n) not in out, "neuron injected twice in one frame"
            out[int(n)] = float(amount)
    return out


def cells_of(eyes, drive, channel):
    """(side, row fraction, col fraction) of every driven neuron in `channel`'s maps."""
    found = []
    for m in eyes.maps:
        if m.channel != channel:
            continue
        for pos, n in enumerate(m.neurons):
            if int(n) in drive:
                row, col = divmod(pos, m.cols)
                found.append((m.side, (row + 0.5) / m.rows, (col + 0.5) / m.cols))
    return found


class TestFlyEyes(unittest.TestCase):
    def test_grid_for_fits_neurons_and_aspect(self):
        for n in (1, 7, 60, 256, 500):
            for aspect in (0.5, 2 / 3, 1.0, 1.5):
                cols, rows = grid_for(n, aspect)
                self.assertGreaterEqual(cols, 1)
                self.assertGreaterEqual(rows, 1)
                self.assertLessEqual(cols * rows, n)
        cols, rows = grid_for(256, 2 / 3)
        self.assertGreater(cols * rows, 200)   # uses most of the neurons

    def test_whole_field_is_seen_at_every_resolution(self):
        """Regression: above 8x8 the old retina only ever saw a strip of the top row."""
        for res in RESOLUTION_PRESETS:
            eyes = FlyEyes(FakeBrain(), res, use_color=False)
            drive = driven(eyes, eyes.inject(frame(blob=(270, 190))))   # bottom-right corner
            spots = cells_of(eyes, drive, "on")
            self.assertTrue(spots, f"{res}: bright object produced no ON drive")
            self.assertTrue(all(side == "R" for side, _, _ in spots), f"{res}: right object drove left eye")
            self.assertGreater(max(r for _, r, _ in spots), 0.6, f"{res}: bottom of screen not seen")
            self.assertGreater(max(c for _, _, c in spots), 0.6, f"{res}: right edge not seen")

    def test_left_half_goes_to_left_eye(self):
        eyes = FlyEyes(FakeBrain(), "64x48", use_color=False)
        drive = driven(eyes, eyes.inject(frame(blob=(20, 20))))
        spots = cells_of(eyes, drive, "on")
        self.assertTrue(spots)
        self.assertTrue(all(side == "L" for side, _, _ in spots))
        self.assertLess(min(r for _, r, _ in spots), 0.4)   # top of the screen

    def test_motion_channel_responds_only_to_change(self):
        eyes = FlyEyes(FakeBrain(), "64x48", use_color=False)
        still = frame(blob=(100, 100))
        eyes.inject(still)
        self.assertFalse(cells_of(eyes, driven(eyes, eyes.inject(still)), "motion"))
        moved = cells_of(eyes, driven(eyes, eyes.inject(frame(blob=(140, 100)))), "motion")
        self.assertTrue(moved)

    def test_drive_is_graded_and_bounded(self):
        eyes = FlyEyes(FakeBrain(), "128x96", use_color=True)
        rng = np.random.default_rng(0)
        img = rng.integers(0, 255, (240, 320, 4), dtype=np.uint8)
        eyes.inject(img)
        drive = driven(eyes, eyes.inject(np.roll(img, 5, axis=1)))
        amounts = np.array(list(drive.values()))
        self.assertTrue(np.all(amounts > 0))
        self.assertTrue(np.all(amounts <= MAX_DRIVE + 1e-6))
        self.assertGreater(len(np.unique(amounts)), 3)          # graded, not all-or-nothing
        self.assertLess(len(drive), eyes.num_neurons)           # not everything saturated

    def test_color_channels_follow_color_mode(self):
        gray_eyes = FlyEyes(FakeBrain(), "64x48", use_color=False)
        color_eyes = FlyEyes(FakeBrain(), "64x48", use_color=True)
        self.assertFalse(set(COLOR_CHANNELS) & set(gray_eyes.channels))
        self.assertTrue(set(COLOR_CHANNELS) <= set(color_eyes.channels))
        self.assertEqual(set(color_eyes.channels), set(CHANNEL_TYPES))

        red = frame()
        red[100:140, 200:240, :3] = (30, 30, 230)   # BGR: a red patch on the right
        drive = driven(color_eyes, color_eyes.inject(red))
        spots = cells_of(color_eyes, drive, "red")
        self.assertTrue(spots)
        self.assertTrue(all(side == "R" for side, _, _ in spots))
        self.assertFalse(cells_of(color_eyes, drive, "blue"))

    def test_gain_control_adapts_to_brightness(self):
        """A dim and a bright version of the same scene drive the eyes about equally."""
        means = []
        for scale in (0.3, 1.0):
            eyes = FlyEyes(FakeBrain(), "64x48", use_color=False)
            img = frame(blob=(150, 100))
            img[:, :, :3] = (img[:, :, :3] * scale).astype(np.uint8)
            for _ in range(20):
                eyes.inject(img)
            means.append(eyes.last_drive["on"])
        self.assertGreater(min(means), 0)
        self.assertLess(max(means) / min(means), 1.5)

    def test_neuron_count_and_description(self):
        eyes = FlyEyes(FakeBrain(per_side=40), "64x48", use_color=True)
        self.assertEqual(eyes.num_neurons, sum(len(m.neurons) for m in eyes.maps))
        self.assertGreater(eyes.num_neurons, 1000)   # far more than the old 128
        self.assertEqual(len(eyes.describe()), len(eyes.channels))

    def test_missing_cell_types_are_skipped(self):
        class SparseBrain(FakeBrain):
            def cells(self, types, side=None):
                if any(t in CHANNEL_TYPES["on"] for t in types):
                    return np.array([], dtype=np.int64)
                return super().cells(types, side)

        eyes = FlyEyes(SparseBrain(), "64x48", use_color=False)
        eyes.inject(frame(blob=(100, 100)))
        self.assertTrue(eyes.inject(frame(blob=(140, 100))))

    def test_unknown_resolution_falls_back(self):
        eyes = FlyEyes(FakeBrain(), "999x999")
        self.assertIn(eyes.resolution, RESOLUTION_PRESETS)


if __name__ == "__main__":
    unittest.main()
