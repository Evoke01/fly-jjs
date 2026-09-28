import unittest

import numpy as np

from fly_jjs.core.casino import (BIG_BET, BOARD_W, MAX_LIFE, RANKS, START_LIFE, Bot, Casino, CasinoFly, ChoiceValues,
                                 Fear, Seat, board_image, likelier_higher, win_chance)
from tests.fakes import fake_components


class TestRules(unittest.TestCase):
    def test_win_chances_and_the_likelier_side(self):
        self.assertAlmostEqual(win_chance(1, True), 12 / 13)
        self.assertEqual(win_chance(1, False), 0.0)          # nothing is lower than an ace
        self.assertAlmostEqual(win_chance(7, True), win_chance(7, False))
        self.assertTrue(likelier_higher(3))
        self.assertFalse(likelier_higher(11))

    def test_bets_pay_out_ties_lose_and_life_is_capped(self):
        seat = Seat("Fly #1")
        seat.place(higher=True, big=True, stake=2)
        self.assertEqual(seat.bet, 2 * BIG_BET)
        self.assertTrue(seat.settle(5, 9))
        self.assertEqual(seat.life, START_LIFE + 6)
        seat.place(higher=False, big=False, stake=1)
        self.assertFalse(seat.settle(8, 8))                  # a tie loses
        self.assertEqual(seat.life, START_LIFE + 5)
        seat.life = MAX_LIFE - 1
        seat.place(True, True, 1)
        seat.settle(1, 13)
        self.assertEqual(seat.life, MAX_LIFE)
        seat.life = 5
        seat.place(True, True, 4)                            # a big bet at stake 4 risks 12
        seat.settle(13, 1)
        self.assertEqual(seat.life, 0)
        self.assertFalse(seat.alive)

    def test_bots(self):
        pro = Bot("pro", np.random.default_rng(0))
        for card in (1, 2, 5, 9, 12, 13):
            higher, big = pro.decide(card)
            self.assertEqual(higher, likelier_higher(card))
            self.assertEqual(big, win_chance(card, higher) >= 0.75)
        rng = np.random.default_rng(0)
        rookie = [Bot("rookie", rng).decide(2)[0] for _ in range(400)]
        self.assertGreater(np.mean(rookie), 0.6)             # usually right...
        self.assertLess(np.mean(rookie), 0.9)                # ...not always
        coin = [Bot("random", rng).decide(2)[0] for _ in range(400)]
        self.assertAlmostEqual(np.mean(coin), 0.5, delta=0.1)
        with self.assertRaises(ValueError):
            Bot("cheater")

    def test_the_board_lights_the_card_in_its_slot(self):
        for card in (1, 7, 13):
            img = board_image(card)
            column = img[:, :, :3].mean(axis=(0, 2))
            brightest = int(np.argmax(column))
            self.assertEqual(brightest * RANKS // BOARD_W + 1, card)
        self.assertLess(board_image()[:, :, :3].mean(), 30)  # empty board is dark


class TestFear(unittest.TestCase):
    def setUp(self):
        self.c = fake_components()

    def test_danger_rises_with_what_is_at_stake(self):
        fear = Fear(self.c, strength=1.0)
        calm = fear.assess(life=START_LIFE, stake=1, dread=0.1)
        self.assertLess(calm, 0.2)
        self.assertGreater(fear.assess(life=3, stake=1, dread=0.1), calm)       # close to death
        self.assertGreater(fear.assess(life=START_LIFE, stake=4, dread=0.1), calm)  # a big loss would hurt
        self.assertGreater(fear.assess(life=START_LIFE, stake=1, dread=0.9), calm)  # it expects to lose
        self.assertEqual(Fear(self.c, strength=0).assess(life=1, stake=4, dread=1.0), 0.0)   # fearless

    def test_terror_is_read_from_the_fear_circuit(self):
        fear = Fear(self.c)
        brain = self.c.brain
        for _ in range(10):
            fear.listen(brain.step())
        quiet = fear.terror
        fear.assess(life=1, stake=4, dread=1.0)
        for _ in range(10):
            fear.listen(brain.step(inject=fear.injections()))
        self.assertLess(quiet, 0.1)
        self.assertGreater(fear.terror, quiet + 0.3)
        self.assertTrue(fear.label())


class TestLearning(unittest.TestCase):
    def test_values_move_toward_what_happened(self):
        values = ChoiceValues(20)
        state = np.zeros(20, dtype=np.float32)
        state[:4] = 1.0
        for _ in range(30):
            values.learn(state, 0, 1.0)
            values.learn(state, 1, -1.0)
        q = values.values(state)
        self.assertGreater(q[0], 0.8)
        self.assertLess(q[1], -0.8)
        # However large the brain state, every update shrinks the error (normalised steps).
        big = np.full(20, 50.0, dtype=np.float32)
        before = abs(1.0 - values.values(big)[0])
        values.learn(big, 0, 1.0)
        after = abs(1.0 - values.values(big)[0])
        self.assertTrue(np.isfinite(after))
        self.assertLess(after, before)

    def test_terror_raises_the_bar_for_a_big_bet(self):
        fly = CasinoFly(fake_components(), {"fear": 1.0}, seed=0)
        fly.values.b[:] = (0.6, -0.6)                        # fairly sure "higher" wins
        fly.fear.terror = 0.0
        calm = np.mean([fly.decide()[2][1] for _ in range(20)])
        fly.fear.terror = 1.0
        scared = np.mean([fly.decide()[2][1] for _ in range(20)])
        self.assertGreater(calm, 0.8)
        self.assertLess(scared, 0.3)

    def test_the_fly_learns_higher_or_lower(self):
        """End to end on the fake brain: eyes on the board, values, dopamine."""
        casino = Casino(fake_components(), {"fear": 1.0}, bot="pro", mode="fast", seed=0, verbose=False)
        while casino.rounds < 300:
            casino.play_game()
        self.assertGreater(casino.stats()["smart_pct"], 80)
        strategy = casino.fly.strategy()
        self.assertGreater(strategy[0]["p_higher"], 0.8)      # ace: say higher
        self.assertLess(strategy[12]["p_higher"], 0.2)        # king: say lower


class TestGames(unittest.TestCase):
    def test_a_killed_fly_is_replaced_and_keeps_its_memory(self):
        casino = Casino(fake_components(), {"fear": 1.0}, bot=None, mode="fast", seed=1, verbose=False)
        casino.fly.values.b[:] = (-5.0, 5.0)                 # a fly sure that everything goes lower...
        casino.fly.values.w[:] = 0.0
        outcome = None
        for _ in range(5):
            outcome = casino.play_game()
            if outcome == "killed":
                break
        self.assertEqual(outcome, "killed")
        self.assertEqual(casino.deaths, 1)
        self.assertEqual(casino.generation, 2)
        self.assertNotEqual(float(casino.fly.values.b[1]), 0.0)   # the next fly keeps the memory
        self.assertEqual(casino.fly.fear.terror, 0.0)             # ...but its brain starts calm

    def test_duels_are_scored(self):
        casino = Casino(fake_components(), {"fear": 1.0}, bot="random", mode="fast", seed=2, verbose=False)
        for _ in range(3):
            casino.play_game()
        self.assertEqual(sum(casino.duels.values()), 3)
        self.assertEqual(casino.games, 3)

    def test_save_and_load(self):
        import os
        import tempfile
        c = fake_components()
        fly = CasinoFly(c, {}, seed=0)
        fly.values.b[:] = (0.25, -0.5)
        fly.usual = np.ones(fly.body.num_inputs, dtype=np.float32)
        path = os.path.join(tempfile.mkdtemp(), "casino_memory.npz")
        fly.save(path)
        again = CasinoFly(c, {}, seed=0)
        self.assertTrue(again.load(path))
        np.testing.assert_allclose(again.values.b, (0.25, -0.5))
        self.assertFalse(CasinoFly(c, {}, seed=0).load(path + ".missing"))

    def test_the_dashboard_gets_the_table_and_can_stop_the_game(self):
        from fly_jjs.core.casino import StopCasino
        from fly_jjs.core.dashboard import BrainDashboard
        c = fake_components()
        dash = BrainDashboard(c.brain)
        casino = Casino(c, {"fear": 1.0}, bot="rookie", mode="fast", seed=0, dashboard=dash, verbose=False)
        casino.play_game(max_rounds=3)
        state = dash.state()
        self.assertEqual(state["mode"], "casino")
        self.assertIn("terror", state["fear"])
        self.assertEqual(len(state["casino"]["strategy"]), RANKS)
        self.assertIn("Rookie", state["title"])
        dash._pokes.append("stop")
        with self.assertRaises(StopCasino):
            casino.play_game()


if __name__ == "__main__":
    unittest.main()
