"""Live 3D view of the fly's whole nervous system, in the browser.

Every neuron of the connectome (166,700) is drawn where it sits in the MaleCNS
reconstruction and lights up when it fires. Sensory neurons have their cell bodies
outside the brain, so the dataset has no position for them; they are drawn on the organs
they belong to: photoreceptors on the compound eyes, lamina neurons just under them,
antennal receptors in the antennae and leg receptors along six legs.

Any mode that runs the brain can stream to it (the arena, Play mode, the casino, the
resting-brain viewer) by attaching a BrainDashboard to the fly's body. The page is
served on 127.0.0.1 only.
"""
import json
import os
import threading
import time
import webbrowser
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import cv2

DEFAULT_PORT = 8765
PAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "brain3d.html")
# Each neuron keeps a fast spike trace (one spike adds 1, decaying over ACTIVITY_TAU) and
# the slow running mean and variance of that trace. The page glows with how unusual a
# neuron's firing is for that neuron (a z-score, in the spirit of dF/F in calcium
# imaging): at rest ~16% of neurons fire every 0.1 s and the olfactory loop bursts on
# its own, which would wash everything out, while what the fly reacts to still lights up.
ACTIVITY_TAU = 0.1      # seconds
BASELINE_TAU = 4.0      # seconds
MIN_SPREAD = 0.3        # floor on a neuron's usual spread, so a silent cell's first spike counts
EXCITED_Z = 2.5         # z-score where the glow starts...
FULL_Z = 6.0            # ...and where it is full
SPARK = 0.18            # faint twinkle for any recent spike
TOP_TYPES = 8
MIN_EXCITED = 3         # excited neurons a cell type needs to be listed

# Display regions: name, colour (RGB, 0..1) and the superclasses drawn in it.
REGIONS = (
    ("Compound eyes", (1.00, 0.58, 0.22), ("ol_sensory",)),
    ("Optic lobes", (0.28, 0.55, 1.00), ("ol_intrinsic",)),
    ("Visual projection", (0.22, 0.88, 0.88), ("visual_projection", "visual_projection_tbc",
                                               "visual_centrifugal")),
    ("Central brain", (0.62, 0.46, 1.00), ("cb_intrinsic", "cb_endocrine", "cb_efferent")),
    ("Mushroom body (memory)", (1.00, 0.42, 0.78), ()),
    ("Reward dopamine (PAM)", (1.00, 0.84, 0.25), ()),
    ("Punishment dopamine (PPL1)", (1.00, 0.22, 0.22), ()),
    ("Descending (brain to body)", (1.00, 0.95, 0.45), ("descending_neuron", "descending_neuron_tbc",
                                                       "efferent_descending")),
    ("Ascending (body to brain)", (0.45, 1.00, 0.50), ("ascending_neuron", "efferent_ascending")),
    ("Nerve cord", (0.40, 0.45, 1.00), ("vnc_intrinsic", "vnc_tbc", "vnc_endocrine")),
    ("Motor neurons", (1.00, 0.62, 0.38), ("vnc_motor", "cb_motor", "vnc_efferent")),
    ("Antennae & head sensors", (0.55, 0.95, 0.78), ("cb_sensory", "cb_sensory_tbc")),
    ("Leg & body sensors", (0.62, 0.82, 0.56), ("vnc_sensory", "vnc_sensory_tbc", "sensory_ascending",
                                                "sensory_ascending_tbc", "sensory_descending")),
    ("Other", (0.62, 0.62, 0.62), ()),
)
REGION_INDEX = {name: i for i, (name, _, _) in enumerate(REGIONS)}
MEMORY_PREFIXES = ("KC", "MBON")

# Circuits the page can highlight (bit flags per neuron).
FEAR, REWARD, MEMORY, MOTOR = 1, 2, 4, 8
FEAR_TYPES = ("LC4", "LPLC2")                 # looming and threat detectors of the eyes
FEAR_GROUPS = ("escape", "backward")          # giant fibre (DNp01) escape, MDN backing away
LAMINA_TYPES = ("L1", "L2", "L3", "L4", "L5", "C2", "C3", "Lai")
LEG_SUPERCLASSES = REGIONS[REGION_INDEX["Leg & body sensors"]][2]
ANTENNA_SUPERCLASSES = REGIONS[REGION_INDEX["Antennae & head sensors"]][2]


def _strings(values, n):
    return np.full(n, "", dtype="<U1") if values is None else np.asarray(values).astype(str)


def _starts(names, prefixes):
    """Element-wise str.startswith for one prefix or a tuple of them."""
    prefixes = (prefixes,) if isinstance(prefixes, str) else prefixes
    return np.logical_or.reduce([np.char.startswith(names, p) for p in prefixes])


def circuit_members(brain):
    """Neuron indices of the circuits the dashboard knows, by name."""
    ct = _strings(brain.cell_type, brain.n)
    groups = getattr(brain, "groups", {}) or {}
    grouped = [np.asarray(groups[k]) for k in groups if k.rsplit("_", 1)[0] in FEAR_GROUPS]
    fear = np.concatenate([np.flatnonzero(np.isin(ct, FEAR_TYPES)),
                           np.flatnonzero(_starts(ct, "PPL1"))] + grouped).astype(np.int64)
    motor = np.concatenate([np.asarray(v) for v in groups.values()]) if groups else np.zeros(0, np.int64)
    return {
        "fear": np.unique(fear),
        "reward": np.flatnonzero(_starts(ct, "PAM")),
        "punish": np.flatnonzero(_starts(ct, "PPL1")),
        "memory": np.flatnonzero(_starts(ct, MEMORY_PREFIXES)),
        "motor": np.unique(motor.astype(np.int64)),
    }


def _unit(v):
    v = np.asarray(v, dtype=np.float64)
    norm = np.linalg.norm(v)
    return v / norm if norm > 0 else v


def neuron_layout(brain, seed=0):
    """Where to draw every neuron. Returns a dict with view-space `positions` (n x 3,
    float32: x = the fly's right, y = up, z = towards the tail), `regions` (uint8 index
    into REGIONS), circuit `flags` (uint8), and the cell-type table for statistics."""
    n = brain.n
    sc, ct, side = _strings(brain.superclass, n), _strings(brain.cell_type, n), _strings(brain.side, n)
    rng = np.random.default_rng(seed)

    regions = np.full(n, REGION_INDEX["Other"], dtype=np.uint8)
    for i, (_, _, superclasses) in enumerate(REGIONS):
        if superclasses:
            regions[np.isin(sc, superclasses)] = i
    regions[_starts(ct, MEMORY_PREFIXES)] = REGION_INDEX["Mushroom body (memory)"]
    regions[_starts(ct, "PAM")] = REGION_INDEX["Reward dopamine (PAM)"]
    regions[_starts(ct, "PPL1")] = REGION_INDEX["Punishment dopamine (PPL1)"]

    members = circuit_members(brain)
    flags = np.zeros(n, dtype=np.uint8)
    for name, bit in (("fear", FEAR), ("reward", REWARD), ("memory", MEMORY), ("motor", MOTOR)):
        flags[members[name]] |= bit

    raw = getattr(brain, "positions", None)
    pos = np.full((n, 3), np.nan) if raw is None else np.array(raw, dtype=np.float64)
    have = np.isfinite(pos).all(axis=1)
    if have.sum() < 10:
        # No anatomy in this build: one cloud per region, so the page still works.
        centres = rng.normal(0, 1.0, (len(REGIONS), 3))
        pos = centres[regions] + rng.normal(0, 0.25, (n, 3))
        return _finish(pos, np.zeros(3), 1.0, np.eye(3), regions, flags, ct)

    brain_pts = have & (sc == "cb_intrinsic")
    centre = pos[brain_pts].mean(0) if brain_pts.any() else pos[have].mean(0)
    vnc_pts = have & np.isin(sc, ("vnc_intrinsic", "vnc_motor"))
    vnc = pos[vnc_pts].mean(0) if vnc_pts.any() else centre + np.array([0.0, 30000.0, 60000.0])
    # Body axes in data coordinates: x is left-right, y dorsal-ventral, z head-tail.
    posterior = np.array([0.0, 0.0, np.sign(vnc[2] - centre[2]) or 1.0])
    ventral = np.array([0.0, np.sign(vnc[1] - centre[1]) or 1.0, 0.0])
    anterior, up = -posterior, -ventral
    lateral, lobe = {}, {}
    for s, default in (("L", 1.0), ("R", -1.0)):
        pts = have & (sc == "ol_intrinsic") & (side == s)
        lobe[s] = pos[pts] if pts.sum() >= 10 else None
        c = lobe[s].mean(0) if lobe[s] is not None else centre
        lateral[s] = np.array([np.sign(c[0] - centre[0]) or default, 0.0, 0.0])
    if lateral["L"][0] == lateral["R"][0]:
        lateral["R"] = -lateral["L"]
    scale = float(np.percentile(np.abs(pos[have] - centre)[:, 0], 99)) or 1.0

    missing = ~have
    # Midline and unknown-side neurons are split between the sides once, at random.
    body_side = np.where(np.isin(side, ("L", "R")), side, np.where(rng.random(n) < 0.5, "L", "R"))
    # Photoreceptors on the compound eyes, the lamina (only partly reconstructed) under them.
    visual = np.asarray(getattr(brain, "visual", np.zeros(0, np.int64)), dtype=np.int64)
    azimuth = np.full(n, np.nan)
    if len(visual) and getattr(brain, "azimuth", None) is not None:
        azimuth[visual] = np.asarray(brain.azimuth, dtype=np.float64)
    eyes = missing & (sc == "ol_sensory")
    typed = _type_centroids(pos, have, ct, side)
    lamina_types = np.isin(ct, LAMINA_TYPES)
    lamina = missing & (sc == "ol_intrinsic") & (lamina_types | ~np.isin(ct, [k for k in typed if isinstance(k, str)]))
    for s in ("L", "R"):
        if lobe[s] is None:
            continue
        c = lobe[s].mean(0)
        known = pos[have & lamina_types & (side == s)]
        # The reconstructed lamina neurons show how far out the lamina sheet lies.
        r_lamina = (float(np.median(np.linalg.norm(known - c, axis=1))) if len(known) >= 20
                    else 0.75 * float(np.max(lobe[s].max(0) - lobe[s].min(0))) / 2)
        for mask, r, spread in ((eyes, 1.28 * r_lamina, 1.0), (lamina, r_lamina, 0.95)):
            idx = np.flatnonzero(mask & (body_side == s))
            if not len(idx):
                continue
            az = azimuth[idx]
            # Azimuth -1 is the far left of the view, +1 the far right; 0 straight ahead.
            toward = np.where(np.isfinite(az), (-az if s == "L" else az), rng.uniform(-0.1, 1.0, len(idx)))
            theta = np.radians(np.clip(toward, -0.15, 1.0) * 100.0)
            golden = (np.arange(len(idx)) * 0.6180339887) % 1.0
            beta = np.radians((golden * 2 - 1) * 62.0 * spread)
            horizontal = np.outer(np.sin(theta), lateral[s]) + np.outer(np.cos(theta), anterior)
            direction = np.cos(beta)[:, None] * horizontal + np.outer(np.sin(beta), up)
            pos[idx] = c + r * direction * rng.uniform(0.985, 1.015, (len(idx), 1))

    # Antennal and other head receptors: two antennae in front of the brain.
    front = float(np.max((pos[brain_pts] - centre) @ anterior)) if brain_pts.any() else 20000.0
    height = float(np.percentile((pos[brain_pts] - centre) @ up, 90)) if brain_pts.any() else 10000.0
    head = missing & np.isin(sc, ANTENNA_SUPERCLASSES)
    for s in ("L", "R"):
        idx = np.flatnonzero(head & (body_side == s))
        if not len(idx):
            continue
        base = centre + anterior * (front + 0.04 * scale) + lateral[s] * 0.14 * scale + up * 0.3 * height
        direction = _unit(anterior + 0.35 * lateral[s] + 0.25 * up)
        t = rng.uniform(0, 1, len(idx))
        pos[idx] = (base + np.outer(t * 0.38 * scale, direction)
                    + rng.normal(0, 1, (len(idx), 3)) * (0.035 * scale * (1.1 - 0.6 * t))[:, None])

    # Leg and body receptors: along three legs on each side of the nerve cord.
    legs = missing & np.isin(sc, LEG_SUPERCLASSES)
    if vnc_pts.any():
        along = (pos[vnc_pts] - centre) @ posterior
        start, end = np.percentile(along, 8), np.percentile(along, 92)
    else:
        start, end = 0.5 * scale, 1.5 * scale
    for s in ("L", "R"):
        idx = np.flatnonzero(legs & (body_side == s))
        if not len(idx):
            continue
        leg = rng.integers(0, 3, len(idx))
        at = start + (np.array([0.2, 0.47, 0.74])[leg]) * (end - start)
        hip = (centre + np.outer(at, posterior) + np.outer(np.ones(len(idx)), vnc - centre) * np.array([1.0, 1.0, 0.0])
               + lateral[s] * 0.12 * scale)
        sweep = np.array([-0.55, 0.0, 0.55])[leg]
        femur = np.array([_unit(lateral[s] + 0.25 * up + sweep[k] * posterior) for k in range(len(idx))])
        tibia = np.array([_unit(0.6 * lateral[s] + 1.0 * ventral + 0.8 * sweep[k] * posterior)
                          for k in range(len(idx))])
        t = rng.uniform(0, 1, len(idx)) ** 0.8
        knee = hip + femur * 0.55 * scale
        on_femur = t < 0.45
        pos[idx] = np.where(on_femur[:, None], hip + femur * (t / 0.45 * 0.55 * scale)[:, None],
                            knee + tibia * ((t - 0.45) / 0.55 * 0.75 * scale)[:, None])
        pos[idx] += rng.normal(0, 0.012 * scale, (len(idx), 3))

    # Everything else without a position: next to its own cell type, else its superclass.
    rest = np.flatnonzero(~np.isfinite(pos).all(axis=1))
    for i in rest:
        s = body_side[i]
        other = "R" if s == "L" else "L"
        if ct[i] and ((ct[i], s) in typed or (ct[i], other) in typed):
            c, sd = typed[(ct[i], s)] if (ct[i], s) in typed else typed[(ct[i], other)]
            if (ct[i], s) not in typed:
                c = c.copy()
                c[0] = 2 * centre[0] - c[0]      # mirror the other side's position
            pos[i] = c + rng.normal(0, 1, 3) * (0.5 * sd + 0.004 * scale)
            continue
        pts = have & (sc == sc[i])
        if pts.sum() >= 10:
            pos[i] = pos[pts].mean(0) + rng.normal(0, 1, 3) * 0.35 * pos[pts].std(0)
        else:
            pos[i] = centre + rng.normal(0, 0.2 * scale, 3)

    # View space: x = the fly's right, y = up, z = towards the tail.
    basis = np.stack([-lateral["L"], up, posterior])
    return _finish(pos, centre, scale, basis, regions, flags, ct)


def _type_centroids(pos, have, ct, side):
    """Centroid and spread of each cell type (and each type on each side) that has positions."""
    out = {}
    names = ct[have]
    sides = side[have]
    pts = pos[have]
    order = np.argsort(names, kind="stable")
    names, sides, pts = names[order], sides[order], pts[order]
    bounds = np.flatnonzero(np.r_[True, names[1:] != names[:-1], True])
    for a, b in zip(bounds[:-1], bounds[1:]):
        name = names[a]
        if not name:
            continue
        group = pts[a:b]
        out[name] = (group.mean(0), group.std(0))
        for s in ("L", "R"):
            on = group[sides[a:b] == s]
            if len(on) >= 2:
                out[(name, s)] = (on.mean(0), on.std(0))
    return out


def _finish(pos, centre, scale, basis, regions, flags, ct):
    view = ((pos - centre) @ basis.T / scale).astype(np.float32)
    types, type_index = np.unique(ct, return_inverse=True)
    return {
        "positions": view,
        "regions": regions,
        "flags": flags,
        "types": types,
        "type_index": type_index.astype(np.int32),
        "type_counts": np.bincount(type_index, minlength=len(types)).astype(np.float32),
        "bounds": [view.min(0).round(3).tolist(), view.max(0).round(3).tolist()],
    }


class BrainDashboard:
    """Streams the brain's spikes and the game's state to the 3D page.

    Call `record(fired)` after every brain step (FlyBody does this for attached
    dashboards), `publish(...)` with whatever the page should show, and `show_eye(img)`
    with what the fly is looking at. Buttons on the page queue "pokes" that the running
    mode can pick up with `take_pokes()`.
    """

    def __init__(self, brain, port=DEFAULT_PORT, layout=None):
        self.brain = brain
        self.n = brain.n
        self.layout = layout or neuron_layout(brain)
        self.members = circuit_members(brain)
        dt = float(getattr(brain, "dt", 0.02))
        self.activity = np.zeros(self.n, dtype=np.float32)     # fast spike trace
        self.baseline = np.zeros(self.n, dtype=np.float32)     # its slow running mean...
        self.variance = np.zeros(self.n, dtype=np.float32)     # ...and variance
        self._diff = np.zeros(self.n, dtype=np.float32)
        self.decay = np.float32(np.exp(-dt / ACTIVITY_TAU))
        self.follow = np.float32(1.0 - np.exp(-dt / BASELINE_TAU))
        self.port = port
        self._lock = threading.Lock()
        self._state = {"mode": "idle"}
        self._counts = deque(maxlen=50)
        self._eye_png = None
        self._pokes = deque(maxlen=32)
        self._server = None
        self._layout_bytes = (self.layout["positions"].tobytes() + self.layout["regions"].tobytes()
                              + self.layout["flags"].tobytes())

    # ---- fed by the simulation --------------------------------------------------------

    def record(self, fired):
        """One brain step's spikes."""
        with self._lock:
            self.activity *= self.decay
            self.activity[fired] += 1.0
            np.subtract(self.activity, self.baseline, out=self._diff)
            self.baseline += self.follow * self._diff
            self._diff *= self._diff
            self._diff -= self.variance
            self.variance += self.follow * self._diff
            self._counts.append(len(fired))

    def attach(self, body):
        """Stream every brain step of a FlyBody."""
        if self.record not in body.listeners:
            body.listeners.append(self.record)
        return self

    def publish(self, **fields):
        with self._lock:
            self._state.update(fields)

    def show_eye(self, img, width=240):
        """What the fly is looking at, for the page's eye view."""
        h, w = img.shape[:2]
        small = cv2.resize(img[:, :, :3], (width, max(1, int(h * width / w))), interpolation=cv2.INTER_AREA)
        ok, png = cv2.imencode(".png", small)
        if ok:
            with self._lock:
                self._eye_png = png.tobytes()

    def take_pokes(self):
        with self._lock:
            pokes = list(self._pokes)
            self._pokes.clear()
        return pokes

    # ---- served to the page -----------------------------------------------------------

    def meta(self):
        counts = np.bincount(self.layout["regions"], minlength=len(REGIONS))
        return {
            "neurons": int(self.n),
            "regions": [{"name": name, "color": list(color), "count": int(counts[i])}
                        for i, (name, color, _) in enumerate(REGIONS)],
            "circuits": {"fear": FEAR, "reward": REWARD, "memory": MEMORY, "motor": MOTOR},
            "circuit_sizes": {k: int(len(v)) for k, v in self.members.items()},
            "bounds": self.layout["bounds"],
        }

    def _traces(self):
        with self._lock:
            return self.activity.copy(), self.baseline.copy(), self.variance.copy()

    @staticmethod
    def excitement(activity, baseline, variance):
        """0..1 per neuron: how unusual its firing is right now, for that neuron."""
        z = (activity - baseline) / np.maximum(np.sqrt(np.maximum(variance, 0.0)), MIN_SPREAD)
        return np.clip((z - EXCITED_Z) / (FULL_Z - EXCITED_Z), 0.0, 1.0)

    def activity_bytes(self, kind="change"):
        """One byte per neuron for the page: how unusual its firing is ("change", with a
        faint twinkle for any spike) or plain recent spiking ("raw")."""
        activity, baseline, variance = self._traces()
        recent = np.minimum(activity, 1.0)
        glow = recent if kind == "raw" else np.maximum(self.excitement(activity, baseline, variance), SPARK * recent)
        return (glow * 255).astype(np.uint8).tobytes()

    def state(self):
        activity, baseline, variance = self._traces()
        with self._lock:
            counts = list(self._counts)
            state = dict(self._state)
        dt = float(getattr(self.brain, "dt", 0.02))
        lay = self.layout
        excited = self.excitement(activity, baseline, variance)
        # Rank cell types by how many of their neurons are excited: one noisy neuron of a
        # single-cell type should not top the list.
        hot = np.bincount(lay["type_index"], weights=(excited > 0.3), minlength=len(lay["types"]))
        hot[lay["types"] == ""] = 0.0
        top = [i for i in np.argsort(-hot, kind="stable")[:TOP_TYPES] if hot[i] >= MIN_EXCITED]
        state["stats"] = {
            "neurons": int(self.n),
            "spikes_per_s": int(np.mean(counts) / dt) if counts else 0,
            "active_pct": round(float(np.count_nonzero(activity >= 0.5)) * 100.0 / self.n, 2),
            "excited_pct": round(float(np.count_nonzero(excited > 0.25)) * 100.0 / self.n, 2),
        }
        state["top_types"] = [{"name": str(lay["types"][i]), "n": int(lay["type_counts"][i]),
                               "excited": int(hot[i]), "pct": round(float(hot[i] / lay["type_counts"][i]) * 100, 1)}
                              for i in top]
        state["circuits"] = {k: round(float(excited[v].mean()), 4) if len(v) else 0.0
                             for k, v in self.members.items()}
        return state

    # ---- server -----------------------------------------------------------------------

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}/"

    def start(self, open_browser=True):
        """Serve the page (local only) and open it in the browser. Returns the URL."""
        if self._server is not None:
            return self.url
        for port in range(self.port, self.port + 20):
            try:
                self._server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
                break
            except OSError:
                continue
        if self._server is None:
            raise OSError(f"no free port in {self.port}..{self.port + 19}")
        self._server.daemon_threads = True
        self._server.dashboard = self
        self.port = self._server.server_address[1]
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        print(f"[Dashboard] 3D brain at {self.url}")
        if open_browser:
            try:
                webbrowser.open(self.url)
            except Exception:
                pass
        return self.url

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None


class _Handler(BaseHTTPRequestHandler):
    def _send(self, body, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        dash = self.server.dashboard
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            try:
                with open(PAGE, "rb") as f:
                    self._send(f.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(b"brain3d.html is missing", "text/plain", 404)
        elif path == "/api/meta":
            self._send(json.dumps(dash.meta()).encode(), "application/json")
        elif path == "/api/layout":
            self._send(dash._layout_bytes, "application/octet-stream")
        elif path == "/api/activity":
            kind = "raw" if "kind=raw" in self.path else "change"
            self._send(dash.activity_bytes(kind), "application/octet-stream")
        elif path == "/api/state":
            self._send(json.dumps(dash.state(), default=_json_default).encode(), "application/json")
        elif path == "/api/eye.png":
            png = dash._eye_png
            if png is None:
                self._send(b"", "image/png", 204)
            else:
                self._send(png, "image/png")
        else:
            self._send(b"not found", "text/plain", 404)

    def do_POST(self):
        dash = self.server.dashboard
        if self.path.split("?", 1)[0] != "/api/poke":
            self._send(b"not found", "text/plain", 404)
            return
        try:
            length = min(int(self.headers.get("Content-Length", 0)), 4096)
            what = str(json.loads(self.rfile.read(length) or b"{}").get("what", ""))[:32]
        except (ValueError, AttributeError):
            self._send(b"bad request", "text/plain", 400)
            return
        with dash._lock:
            dash._pokes.append(what)
        self._send(b"{}", "application/json")

    def log_message(self, format, *args):
        pass


def _json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    return str(value)


# ---- the resting-brain viewer ([B] in the menu) ----------------------------------------

POKES = ("loom", "flash", "reward", "punish")
LOOM_STEPS = 40          # 0.8 s of brain time


def poke_frames(what, width=160, height=120, steps=LOOM_STEPS):
    """The image sequence the fly sees for a poke (dark room otherwise)."""
    frames = []
    for k in range(steps):
        img = np.full((height, width, 4), 40, dtype=np.uint8)
        img[:, :, 3] = 255
        if what == "loom":
            # A dark disk rushing at the fly: the classic stimulus for the escape reflex.
            radius = int(4 + (min(width, height) * 0.9) * (k / steps) ** 3)
            img[:, :, :3] = 170
            cv2.circle(img, (width // 2, height // 2), radius, (15, 15, 15, 255), -1)
        elif what == "flash" and k < 6:
            img[:, :, :3] = 255
        frames.append(img)
    return frames


def run_brain_viewer(seconds=None, open_browser=True):
    """Run the brain in real time with the 3D page open; the page's buttons poke it."""
    from fly_jjs.core.brain import FlyBody, get_brain_components
    from fly_jjs.core.config import ConfigManager
    from fly_jjs.core.vision import FlyEyes

    cfg = ConfigManager.load_config()
    c = get_brain_components()
    body = FlyBody(c, FlyEyes(c.brain, cfg.get("resolution", "64x48"), cfg.get("use_color", True)))
    dash = BrainDashboard(c.brain, port=cfg.get("dashboard_port", DEFAULT_PORT)).attach(body)
    dash.start(open_browser=open_browser)
    dark = poke_frames("none", steps=1)[0]
    queue, poke, dopamine = [], "", 0.0
    dash.publish(mode="resting", title="Resting fly brain", pokes=list(POKES), log=[])
    log = deque(maxlen=6)
    started = time.time()
    print("[Dashboard] Running the brain in real time. Press Ctrl+C (or Stop on the page) to finish.")
    try:
        while seconds is None or time.time() - started < seconds:
            for what in dash.take_pokes():
                if what == "stop":
                    return dash
                if what in POKES:
                    poke = what
                    queue = poke_frames(what) if what in ("loom", "flash") else [dark] * 12
                    dopamine = {"reward": 1.0, "punish": -1.0}.get(what, 0.0)
                    log.appendleft({"loom": "Looming shadow shown", "flash": "Flash of light",
                                    "reward": "Reward dopamine released",
                                    "punish": "Punishment dopamine released"}[what])
            img = queue.pop(0) if queue else dark
            looming = poke == "loom" and bool(queue)
            growth = (1.0 - len(queue) / LOOM_STEPS) if looming else 0.0
            tick = time.time()
            body.step(img, (0, 0, 40 + 200 * growth) if looming else (0, 0, 0), growth if looming else 0.0,
                      dopamine if queue else 0.0)
            if not queue:
                poke, dopamine = "", 0.0
            if body.c.brain.steps % 3 == 0:
                dash.show_eye(img)
                dash.publish(t=round(time.time() - started, 1), poke=poke, log=list(log))
            time.sleep(max(0.0, body.c.brain.dt - (time.time() - tick)))
    except KeyboardInterrupt:
        pass
    finally:
        dash.stop()
    return dash
