"""The fly's nervous system as the game sees it: what we stimulate and what we read.

Every frame the whole connectome (166,700 neurons) is simulated. The learner reads a
readout population of ~59,000 neurons: everything downstream of the eyes (visual
projection neurons, the central brain, ascending and descending neurons, the ventral
nerve cord and motor neurons). The optic lobe's own ~89,000 columnar neurons and the
sensory neurons sit upstream of where the eyes inject, so they are left out.
"""
from types import SimpleNamespace

import numpy as np
from flybrain import FeatureDetectors, FlyBrain, Trace

from fly_jjs.core.actions import ACTION_NAMES, NUM_ACTIONS

READOUT_SUPERCLASSES = (
    "descending_neuron", "descending_neuron_tbc",
    "visual_projection", "visual_projection_tbc", "visual_centrifugal",
    "cb_intrinsic", "cb_motor", "cb_efferent", "cb_endocrine",
    "ascending_neuron", "vnc_intrinsic", "vnc_motor", "vnc_efferent", "vnc_endocrine", "vnc_tbc",
    "efferent_ascending", "efferent_descending",
)

# Innate drive: when an action's motor population fires at its threshold rate, the
# untrained fly presses that key half the time. INNATE_GAIN sets how sharply the odds
# follow the population's rate; instincts and learning add to this.
BASE_THRESHOLDS = {
    "forward": 0.12, "left": 0.12, "back": 0.15, "right": 0.12,
    "melee": 0.18,
    "skill1": 0.22, "skill2": 0.22, "skill3": 0.22, "skill4": 0.22,
    "dash": 0.20, "block": 0.18, "special": 0.25,
    "sprint": 0.28, "awaken": 0.35, "jump": 0.30,
}
INNATE_GAIN = 12.0
READOUT_TAU = 0.1       # seconds: neurons are read as a decaying spike trace
DOPAMINE_DRIVE = 0.8    # voltage per step on dopamine neurons at full surprise

_components = None


def readout_neurons(brain, dns, full=True):
    """Descending neurons first (older weight files map onto them), then the rest."""
    if not full or getattr(brain, "superclass", None) is None:
        return np.asarray(dns)
    everything = np.flatnonzero(np.isin(brain.superclass.astype(str), READOUT_SUPERCLASSES))
    return np.concatenate([dns, np.setdiff1d(everything, dns)])


def get_brain_components():
    """Load the connectome once and pick out the neurons the game talks to."""
    global _components
    if _components is None:
        print("\n[Brain] Loading connectome...")
        brain = FlyBrain(device="cpu")
        dns = brain.cells(["descending_neuron"])
        cell_types = [str(t) for t in np.unique(brain.cell_type)]
        # Reward (PAM) and punishment (PPL1) dopamine neurons of the mushroom body.
        reward_dans = brain.cells([t for t in cell_types if t.startswith("PAM")])
        punish_dans = brain.cells([t for t in cell_types if t.startswith("PPL1")])
        pop_size = len(dns) // NUM_ACTIONS
        populations = [slice(i * pop_size, (i + 1) * pop_size) for i in range(NUM_ACTIONS)]
        readout = readout_neurons(brain, dns)
        _components = SimpleNamespace(brain=brain, fd=FeatureDetectors(brain), dns=dns, readout=readout,
                                      reward_dans=reward_dans, punish_dans=punish_dans,
                                      populations=populations)
        print(f"[Brain] Reading {len(readout):,} neurons ({len(dns):,} descending) out of {brain.n:,}; "
              f"{len(reward_dans)} reward / {len(punish_dans)} punishment dopamine neurons")
    return _components


class FlyBody:
    """One game frame in, firing rates of the readout neurons out.

    `steps` brain steps (20 ms each) are simulated per frame. More steps give the
    readout more spikes to average, so more of what the fly sees reaches its decisions.
    """

    def __init__(self, components, eyes, steps=1, readout=None):
        self.c = components
        self.eyes = eyes
        self.steps = max(1, int(steps))
        self.readout = np.asarray(components.readout if readout is None else readout)
        self.num_dns = len(components.dns)
        self.trace = Trace(components.brain, idx=self.readout, tau=READOUT_TAU)
        self.rate_scale = 1.0 - float(self.trace.decay)   # trace -> spikes per step (0..1)
        self.arousal = 0.0
        self.fired = 0
        self.rates = np.zeros(len(self.readout), dtype=np.float32)

    @property
    def num_inputs(self):
        return len(self.readout)

    def step(self, img, opp, threat, dopamine=0.0, pattern_burst=False):
        c = self.c
        opp_pos = (opp[0], opp[2]) if opp[2] > 0 else None
        if pattern_burst:
            # A predicted burst is an attack about to land: drive the looming/escape pathway.
            threat = max(threat, 0.8)
        injections = c.fd.inject(opp=opp_pos, threat=threat)
        injections += self.eyes.inject(img)
        if dopamine > 0.05 and len(c.reward_dans):
            injections.append((c.reward_dans, min(dopamine, 1.0) * DOPAMINE_DRIVE))
        elif dopamine < -0.05 and len(c.punish_dans):
            injections.append((c.punish_dans, min(-dopamine, 1.0) * DOPAMINE_DRIVE))

        for _ in range(self.steps):
            fired = c.brain.step(inject=injections)
            self.rates = self.trace.observe(fired) * self.rate_scale
        self.fired = len(fired)
        activity = float(np.mean(self.rates[:self.num_dns]))
        self.arousal = min(self.arousal * 0.95 + activity * 0.15, 1.0)
        return self.rates

    def innate_drive(self, rates):
        """Per-action logits from the descending-neuron motor populations, and their rates."""
        pop_rates = np.array([rates[p].mean() for p in self.c.populations], dtype=np.float32)
        logits = np.empty(NUM_ACTIONS, dtype=np.float32)
        for i, name in enumerate(ACTION_NAMES):
            threshold = BASE_THRESHOLDS[name]
            if name in ("forward", "left", "right", "melee"):
                threshold *= 1.0 - self.arousal * 0.3
            logits[i] = INNATE_GAIN * (pop_rates[i] - threshold)
        return logits, pop_rates
