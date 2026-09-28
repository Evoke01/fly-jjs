import json
import unittest
import urllib.request

import numpy as np

from fly_jjs.core.dashboard import (FEAR, MEMORY, REGION_INDEX, REGIONS, BrainDashboard, circuit_members,
                                    neuron_layout, poke_frames)
from tests.fakes import FakeBrain


class TestLayout(unittest.TestCase):
    def setUp(self):
        self.brain = FakeBrain()
        self.lay = neuron_layout(self.brain)

    def test_every_neuron_gets_a_place_and_a_region(self):
        pos = self.lay["positions"]
        self.assertEqual(pos.shape, (self.brain.n, 3))
        self.assertTrue(np.all(np.isfinite(pos)))
        self.assertTrue(np.all(self.lay["regions"] < len(REGIONS)))

    def test_sensory_neurons_sit_on_their_organs(self):
        """They have no positions in the data (their cell bodies are outside the brain)."""
        pos, reg = self.lay["positions"], self.lay["regions"]
        brain_part = pos[reg == REGION_INDEX["Central brain"]]
        eyes = pos[reg == REGION_INDEX["Compound eyes"]]
        antennae = pos[reg == REGION_INDEX["Antennae & head sensors"]]
        legs = pos[reg == REGION_INDEX["Leg & body sensors"]]
        cord = pos[reg == REGION_INDEX["Nerve cord"]]
        centre = brain_part.mean(0)
        # Eyes out to the sides, antennae in front (z is towards the tail), legs by the cord.
        self.assertGreater(np.abs(eyes[:, 0] - centre[0]).mean(), np.abs(brain_part[:, 0] - centre[0]).mean())
        self.assertLess(antennae[:, 2].mean(), brain_part[:, 2].min())
        self.assertGreater(legs[:, 2].mean(), centre[2])
        self.assertGreater(cord[:, 2].mean(), centre[2])
        # The fly's left eye (side L) is drawn on the fly's left: x points to the fly's right.
        left = self.brain.side[reg == REGION_INDEX["Compound eyes"]] == "L"
        self.assertLess(eyes[left, 0].mean(), eyes[~left, 0].mean())

    def test_circuits(self):
        members = circuit_members(self.brain)
        ct = self.brain.cell_type
        self.assertTrue(set(ct[members["fear"]]) >= {"LC4", "LPLC2", "PPL101", "DNp01"})
        self.assertEqual(set(ct[members["reward"]]), {"PAM01"})
        self.assertTrue(np.all(self.lay["flags"][members["fear"]] & FEAR))
        self.assertTrue(np.all(self.lay["flags"][members["memory"]] & MEMORY))

    def test_works_without_positions(self):
        self.brain.positions = None
        lay = neuron_layout(self.brain)
        self.assertTrue(np.all(np.isfinite(lay["positions"])))


class TestActivity(unittest.TestCase):
    def test_unusual_firing_glows_and_steady_firing_does_not(self):
        brain = FakeBrain()
        dash = BrainDashboard(brain)
        steady, burst = np.arange(0, 20), np.arange(100, 120)
        for t in range(400):                                   # steady neurons fire every other step
            dash.record(steady if t % 2 == 0 else np.zeros(0, np.int64))
        for _ in range(4):                                     # then a silent group bursts
            dash.record(np.concatenate([steady, burst]))
        glow = np.frombuffer(dash.activity_bytes("change"), dtype=np.uint8)
        self.assertGreater(glow[burst].mean(), 200)
        self.assertLess(glow[steady].mean(), 80)
        raw = np.frombuffer(dash.activity_bytes("raw"), dtype=np.uint8)
        self.assertEqual(raw[steady].min(), 255)                # raw mode shows every recent spike
        state = dash.state()
        self.assertGreater(state["stats"]["spikes_per_s"], 0)
        self.assertIn(state["top_types"][0]["name"], set(brain.cell_type[burst]))

    def test_listener_on_the_body(self):
        from fly_jjs.core.brain import FlyBody
        from fly_jjs.core.vision import FlyEyes
        from tests.fakes import fake_components
        c = fake_components()
        body = FlyBody(c, FlyEyes(c.brain, "64x48", True))
        dash = BrainDashboard(c.brain).attach(body)
        dash.attach(body)                                      # attaching twice is harmless
        self.assertEqual(body.listeners.count(dash.record), 1)
        body.step(poke_frames("flash")[0], (0, 0, 0), 0.0)
        self.assertEqual(len(dash._counts), 1)


class TestServer(unittest.TestCase):
    def test_the_page_and_its_api(self):
        brain = FakeBrain()
        dash = BrainDashboard(brain, port=18765)
        url = dash.start(open_browser=False)
        try:
            def get(path):
                with urllib.request.urlopen(url + path, timeout=5) as r:
                    return r.status, r.headers.get("Content-Type"), r.read()
            status, kind, page = get("")
            self.assertEqual(status, 200)
            self.assertIn("text/html", kind)
            self.assertIn(b"/api/layout", page)
            meta = json.loads(get("api/meta")[2])
            self.assertEqual(meta["neurons"], brain.n)
            self.assertEqual(len(get("api/layout")[2]), brain.n * 14)   # 3 floats + region + flags
            self.assertEqual(len(get("api/activity")[2]), brain.n)
            self.assertEqual(len(get("api/activity?kind=raw")[2]), brain.n)
            self.assertEqual(get("api/eye.png")[0], 204)            # nothing seen yet
            dash.show_eye(poke_frames("loom")[20])
            self.assertEqual(get("api/eye.png")[2][:4], b"\x89PNG")
            dash.publish(mode="resting", title="test")
            self.assertEqual(json.loads(get("api/state")[2])["mode"], "resting")
            req = urllib.request.Request(url + "api/poke", data=b'{"what": "loom"}', method="POST")
            urllib.request.urlopen(req, timeout=5).read()
            self.assertEqual(dash.take_pokes(), ["loom"])
            self.assertTrue(url.startswith("http://127.0.0.1:"))     # local only
        finally:
            dash.stop()


if __name__ == "__main__":
    unittest.main()
