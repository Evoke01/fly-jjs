"""The fly's eyes: turn a captured game frame into drive for the fly's visual neurons.

The old front end copied the first 64 pixels of the frame onto 128 hand-picked neurons.
Above 8x8 that was only a strip of the top row, and at 5x voltage it saturated every
neuron it touched. This one works like a compound eye:

1. The frame is shrunk to the chosen processing grid (8x8 ... 320x240).
2. Feature maps are computed at that resolution, the way the fly's early visual system
   splits a scene: ON contrast (brighter than the surroundings), OFF contrast (darker),
   motion (what changed since the last frame) and, in colour mode, red and blue.
3. The left half of the screen goes to the left eye and the right half to the right eye.
   Each feature is carried by its own visual projection neuron types. Every type tiles
   its whole half of the visual field, one receptive field per neuron (retinotopic).
4. Each neuron receives how much its receptive field stands out from the rest of the
   view (global surround inhibition: a textured floor stays quiet, an opponent or a
   flash does not), scaled by adaptive gain control like photoreceptor adaptation, so
   dark scenes, bright scenes and every resolution give a similar, graded drive.

Types were chosen from the MaleCNS connectome for their direct synapses onto descending
neurons, so what the eyes see reaches the fly's motor commands instead of dying out in
the central brain. flybrain.FeatureDetectors keeps its own types (LC4, LPLC2, LPLC1,
LC10a) for looming and target chasing, which this module does not touch.
"""
import numpy as np
import cv2

from fly_jjs.core.config import RESOLUTION_PRESETS

# Feature channel -> visual projection neuron types that carry it (per eye).
CHANNEL_TYPES = {
    "motion": ("LPLC4", "LLPC1", "LLPC2", "LLPC3", "LPC1"),   # lobula plate: motion
    "on": ("MTe01b", "LC22"),                                  # brighter than surroundings
    "off": ("LC9", "LC18"),                                    # darker than surroundings
    "red": ("aMe5", "LC6", "LC16"),                            # colour mode only
    "blue": ("LC29", "LC10c", "LC10d"),                        # colour mode only
}
COLOR_CHANNELS = ("red", "blue")
MAX_DRIVE = 1.0     # most voltage one neuron gets per step (the spike threshold is 1.0)
LEVELS = 8          # drive is quantised so each type needs only a few inject calls
MIN_CONTRAST = 0.02 # features weaker than this never reach full drive (no noise blow-up)
SIDES = ("L", "R")


def grid_for(n, aspect):
    """Largest (cols, rows) grid with cols * rows <= n and cols / rows close to `aspect`."""
    rows = max(1, int(np.sqrt(n / aspect)))
    cols = max(1, min(n // rows, int(round(rows * aspect))))
    return cols, rows


class _Map:
    """One neuron type on one side, laid out as a grid over that half of the screen."""

    def __init__(self, channel, side, cell_type, neurons, aspect):
        self.channel, self.side, self.cell_type = channel, side, cell_type
        self.cols, self.rows = grid_for(len(neurons), aspect)
        self.neurons = np.asarray(neurons)[:self.cols * self.rows]


class FlyEyes:
    """Retinotopic, per-eye visual encoder for a flybrain.FlyBrain."""

    def __init__(self, brain, resolution="64x48", use_color=True, frame_aspect=4 / 3):
        self.resolution = resolution if resolution in RESOLUTION_PRESETS else "64x48"
        self.width, self.height = RESOLUTION_PRESETS[self.resolution]
        self.use_color = use_color
        self.channels = [c for c in CHANNEL_TYPES if use_color or c not in COLOR_CHANNELS]
        self.maps = []
        for channel in self.channels:
            for side in SIDES:
                for cell_type in CHANNEL_TYPES[channel]:
                    neurons = brain.cells([cell_type], side=side)
                    if len(neurons):
                        self.maps.append(_Map(channel, side, cell_type, neurons, frame_aspect / 2))
        self.num_neurons = sum(len(m.neurons) for m in self.maps)
        self._by_channel = {c: [k for k, m in enumerate(self.maps) if m.channel == c] for c in self.channels}
        # A connectome build without some of these types just gets fewer channels.
        self._by_channel = {c: members for c, members in self._by_channel.items() if members}
        self.previous = None
        self.gain = {c: 0.0 for c in self.channels}
        self.last_drive = {c: 0.0 for c in self.channels}   # mean drive per channel, for display

    def describe(self):
        """Human-readable summary: neurons and receptive-field grid per channel and eye."""
        lines = []
        for channel in self.channels:
            maps = [m for m in self.maps if m.channel == channel]
            total = sum(len(m.neurons) for m in maps)
            grids = ", ".join(f"{m.cell_type}-{m.side} {m.cols}x{m.rows}" for m in maps)
            lines.append(f"{channel:>6}: {total:4d} neurons ({grids})")
        return lines

    def features(self, img):
        """Feature maps (values >= 0) at the processing resolution."""
        small = cv2.resize(img[:, :, :3], (self.width, self.height), interpolation=cv2.INTER_AREA)
        small = small.astype(np.float32) / 255.0
        lum = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        # Centre-surround contrast: each point against its neighbourhood, like the lamina.
        surround = cv2.GaussianBlur(lum, (0, 0), max(1.0, self.width / 16))
        contrast = lum - surround
        maps = {
            "on": np.maximum(contrast, 0.0),
            "off": np.maximum(-contrast, 0.0),
            "motion": np.zeros_like(lum) if self.previous is None else np.abs(lum - self.previous),
        }
        self.previous = lum
        if self.use_color:
            b, g, r = small[:, :, 0], small[:, :, 1], small[:, :, 2]
            maps["red"] = np.maximum(r - (g + b) / 2, 0.0)
            maps["blue"] = np.maximum(b - (r + g) / 2, 0.0)
        return maps

    def reset(self):
        self.previous = None

    def inject(self, img):
        """Drive for this frame, as (neuron indices, voltage) pairs for FlyBrain.step."""
        maps = self.features(img)
        half = max(1, self.width // 2)
        pooled = []
        for m in self.maps:
            fmap = maps[m.channel]
            field = fmap[:, :half] if m.side == "L" else fmap[:, -half:]
            pooled.append(cv2.resize(field, (m.cols, m.rows), interpolation=cv2.INTER_AREA).ravel())

        injections = []
        for c, members in self._by_channel.items():
            # Global surround inhibition: only what stands out from the rest of the view
            # drives neurons, so a textured floor stays quiet while an opponent or a flash
            # does not.
            mean = float(np.mean(np.concatenate([pooled[k] for k in members])))
            peak = 0.0
            for k in members:
                pooled[k] = np.maximum(pooled[k] - mean, 0.0)
                peak = max(peak, float(np.percentile(pooled[k], 98)))
            # Adaptive gain: follow the channel's recent strong responses, so the strongest
            # features drive neurons near threshold without pinning everything at maximum.
            self.gain[c] = peak if self.gain[c] == 0.0 else 0.9 * self.gain[c] + 0.1 * peak
            scale = max(self.gain[c], MIN_CONTRAST)

            total = 0.0
            count = 0
            for k in members:
                level = np.minimum(np.round(pooled[k] / scale * LEVELS), LEVELS).astype(np.int32)
                neurons = self.maps[k].neurons
                total += float(level.sum())
                count += len(neurons)
                for lv in range(1, LEVELS + 1):
                    chosen = neurons[level == lv]
                    if len(chosen):
                        injections.append((chosen, MAX_DRIVE * lv / LEVELS))
            self.last_drive[c] = total * MAX_DRIVE / LEVELS / max(count, 1)
        return injections


def get_pixel_grids(img, resolution_preset="8x8", use_color=True):
    """Red/blue (or grey) pixel grids of the frame, plus the full-size grey image.

    Kept for tools and tests that want a plain downsampled view; the fly itself sees
    through FlyEyes.
    """
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
    """Largest bright blob in the middle band of the screen.

    Returns ((dx, dy, size), threat) relative to the screen centre; size is 0 when
    nothing was found.
    """
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
                cy = int(M["m01"] / M["m00"]) + y1
                dx = cx - (width // 2)
                dy = cy - (height // 2)
                threat = min(1.0, size / 70.0)
                return (dx, dy, size), threat
    return (0, 0, 0), 0.0


def detect_motion(gray, prev):
    if prev is None:
        return 0.0
    return float(np.mean(cv2.absdiff(gray, prev)) / 255.0)
