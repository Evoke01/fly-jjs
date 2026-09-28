"""A tiny stand-in for flybrain.FlyBrain, so the casino and the 3D dashboard can be tested
without the 260 MB connectome: neurons fire when injected past threshold (plus a little
noise), and the cell types the eyes and the fear circuit look for exist."""
from types import SimpleNamespace

import numpy as np

from fly_jjs.core.vision import CHANNEL_TYPES


class FakeBrain:
    dt = 0.020
    batch = 1

    def __init__(self, per_type=40, seed=0):
        names, sides, supers = [], [], []

        def add(cell_type, count, superclass, side):
            names.extend([cell_type] * count)
            sides.extend([side] * count)
            supers.extend([superclass] * count)

        for types in CHANNEL_TYPES.values():
            for t in types:
                for s in "LR":
                    add(t, per_type, "visual_projection", s)
        for s in "LR":
            add("LC4", 10, "visual_projection", s)
            add("LPLC2", 10, "visual_projection", s)
            add("PPL101", 4, "cb_intrinsic", s)
            add("PAM01", 6, "cb_intrinsic", s)
            add("KCg-m", 20, "cb_intrinsic", s)
            add("SMP001", 20, "cb_intrinsic", s)
            add("DNp01", 1, "descending_neuron", s)
            add("DNa02", 15, "descending_neuron", s)
            add("R1-6", 12, "ol_sensory", s)        # photoreceptors: no positions, like the real data
            add("ORN_DA1", 8, "cb_sensory", s)      # antennal receptors: no positions either
            add("LgLG1a", 8, "vnc_sensory", s)      # leg receptors: no positions either
            add("IN01A001", 20, "vnc_intrinsic", s)
            add("Tm3", 30, "ol_intrinsic", s)
        self.cell_type = np.array(names)
        self.side = np.array(sides)
        self.superclass = np.array(supers)
        self.n = len(names)
        rng = np.random.default_rng(seed)
        centre = {"visual_projection": (0, 0, 0), "cb_intrinsic": (0, 0, 0), "descending_neuron": (0, -2000, 3000),
                  "vnc_intrinsic": (0, 30000, 70000), "ol_intrinsic": (30000, 0, 0)}
        pos = np.full((self.n, 3), np.nan)
        for i in range(self.n):
            if self.superclass[i] in centre:
                c = np.array(centre[self.superclass[i]], dtype=float)
                if self.superclass[i] in ("visual_projection", "ol_intrinsic"):
                    c[0] = 30000 if self.side[i] == "L" else -30000
                pos[i] = c + rng.normal(0, 4000, 3)
        pos[:, 0] += 48000
        self.positions = pos
        self.groups = {"escape_L": self.cells(["DNp01"], "L"), "escape_R": self.cells(["DNp01"], "R")}
        self.visual = self.cells(["R1-6"])
        self.azimuth = np.linspace(-1, 1, len(self.visual))
        self.reset(seed)

    def cells(self, types, side=None):
        mask = np.isin(self.cell_type, types) | np.isin(self.superclass, types)
        if side:
            mask &= self.side == side
        return np.flatnonzero(mask)

    def reset(self, seed=None):
        self.rng = np.random.default_rng(seed)
        self.v = np.zeros(self.n, dtype=np.float32)
        self.steps = 0

    def step(self, eye_drive=None, inject=()):
        self.v *= 0.6
        self.v += (self.rng.random(self.n) < 0.02) * 0.6
        for idx, amount in inject:
            self.v[np.asarray(idx)] += amount
        fired = np.flatnonzero(self.v >= 1.0)
        self.v[fired] = 0.0
        self.steps += 1
        return fired


def fake_components(seed=0):
    """What fly_jjs.core.brain.get_brain_components returns, for a FakeBrain."""
    from fly_jjs.core.actions import NUM_ACTIONS
    brain = FakeBrain(seed=seed)
    dns = brain.cells(["descending_neuron"])
    pop = len(dns) // NUM_ACTIONS
    return SimpleNamespace(
        brain=brain, fd=SimpleNamespace(inject=lambda opp=None, threat=0.0: []), dns=dns,
        readout=np.arange(brain.n), reward_dans=brain.cells(["PAM01"]), punish_dans=brain.cells(["PPL101"]),
        populations=[slice(i * pop, (i + 1) * pop) for i in range(NUM_ACTIONS)])
