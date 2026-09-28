import unittest

from fly_jjs.core.controls import MELEE_INTERVAL, CameraController, InputController, RecordingBackend


def events(backend, kind):
    return [key for k, key in backend.events if k == kind]


class TestInputController(unittest.TestCase):
    def setUp(self):
        self.backend = RecordingBackend()
        self.ctl = InputController(self.backend)

    def test_movement_is_held_not_tapped(self):
        """Regression: keys used to be tapped for one frame, so the character barely moved."""
        for t in range(5):
            self.ctl.apply({"forward", "left"}, now=t * 0.05)
        self.assertEqual(self.backend.held, {"w", "a"})
        self.assertEqual(events(self.backend, "down").count("w"), 1)   # pressed once, then held
        self.assertNotIn("w", events(self.backend, "tap"))
        self.ctl.apply({"left"}, now=0.3)
        self.assertEqual(self.backend.held, {"a"})
        self.assertIn("w", events(self.backend, "up"))

    def test_block_is_held_and_stops_clicks(self):
        self.ctl.apply({"block", "melee"}, now=0.0)
        self.assertIn("f", self.backend.held)
        self.assertEqual(events(self.backend, "click"), [])

    def test_melee_clicks_at_a_combo_rhythm(self):
        t = 0.0
        while t < 1.0:
            self.ctl.apply({"melee"}, now=t)
            t += 0.05
        clicks = len(events(self.backend, "click"))
        self.assertGreaterEqual(clicks, int(1.0 / MELEE_INTERVAL) - 1)
        self.assertLessEqual(clicks, int(1.0 / MELEE_INTERVAL) + 1)

    def test_skills_are_tapped_once_per_switch_on(self):
        for t in range(10):
            self.ctl.apply({"skill1", "jump"}, now=t * 0.05)
        self.assertEqual(events(self.backend, "tap").count("1"), 1)
        self.assertEqual(events(self.backend, "tap").count("space"), 1)
        self.ctl.apply(set(), now=1.0)
        self.ctl.apply({"skill1"}, now=1.05)
        self.assertEqual(events(self.backend, "tap").count("1"), 2)

    def test_sprint_double_taps_then_holds_w(self):
        self.ctl.apply({"forward"}, now=0.0)
        self.ctl.apply({"forward", "sprint"}, now=0.05)
        self.assertIn("w", events(self.backend, "tap"))
        self.assertIn("w", self.backend.held)

    def test_a_clock_that_starts_over_still_clicks(self):
        """Regression: arena fights restart the clock at 0. The last click at t=36 s of the
        previous fight blocked every click of the next fight until t=36 s."""
        self.ctl.apply({"melee", "skill1"}, now=36.0)
        self.ctl.apply(set(), now=36.05)
        clicks, taps = len(events(self.backend, "click")), events(self.backend, "tap").count("1")
        self.ctl.apply({"melee", "skill1"}, now=0.0)
        self.assertEqual(len(events(self.backend, "click")), clicks + 1)
        self.assertEqual(events(self.backend, "tap").count("1"), taps + 1)

    def test_opposite_keys_are_never_held_together(self):
        self.ctl.apply({"forward", "back", "left", "right"}, now=0.0)
        self.assertEqual(self.backend.held, set())              # both new: neither
        self.ctl.apply({"forward"}, now=0.05)
        executed = self.ctl.apply({"forward", "back"}, now=0.1)
        self.assertEqual(self.backend.held, {"w"})              # keep the one already going
        self.assertEqual(executed, {"forward"})

    def test_release_all_lets_go_of_everything(self):
        self.ctl.apply({"forward", "block", "right"}, now=0.0)
        self.ctl.release_all()
        self.assertEqual(self.backend.held, set())


class TestCameraController(unittest.TestCase):
    def test_turns_toward_the_opponent(self):
        backend = RecordingBackend()
        cam = CameraController(backend, 640, 480, sensitivity=0.3)
        dx, _ = cam.update((200, 0), now=0.0)
        self.assertGreater(dx, 0)
        dx, _ = cam.update((-200, 0), now=0.05)
        self.assertLess(dx, 0)

    def test_dead_zone_and_clamp(self):
        backend = RecordingBackend()
        cam = CameraController(backend, 640, 480, sensitivity=0.3, max_step=50)
        self.assertEqual(cam.update((5, 3), now=0.0), (0, 0))
        dx, _ = cam.update((5000, 0), now=0.05)
        self.assertLessEqual(dx, 50)

    def test_searches_when_nobody_is_in_view(self):
        backend = RecordingBackend()
        cam = CameraController(backend, 640, 480)
        cam.update((50, 0), now=0.0)
        self.assertEqual(cam.update(None, now=0.5), (0, 0))      # just lost them: wait
        dx, _ = cam.update(None, now=3.0)                         # still gone: sweep
        self.assertGreater(dx, 0)

    def test_search_works_in_any_clock(self):
        """Regression: the search timer started from wall-clock time, so a simulated clock
        starting at 0 never searched."""
        backend = RecordingBackend()
        cam = CameraController(backend, 640, 480)
        self.assertEqual(cam.update(None, now=0.0), (0, 0))
        dx, _ = cam.update(None, now=2.0)
        self.assertGreater(dx, 0)
        cam.reset()
        self.assertEqual(cam.update(None, now=0.0), (0, 0))   # a new fight starts calm

    def test_hold_right_button_mode(self):
        backend = RecordingBackend()
        cam = CameraController(backend, 640, 480, hold_right_button=True)
        cam.update((200, 0), now=0.0)
        kinds = [k for k, _ in backend.events]
        self.assertEqual(kinds, ["rmb", "move", "rmb"])


if __name__ == "__main__":
    unittest.main()
