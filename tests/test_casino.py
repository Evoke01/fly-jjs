import unittest

import numpy as np

from fly_jjs.core.casino import (BIG_BET, BOARD_W, FINAL_STAKE, RANKS, ROUNDS, START_CHIPS, SUDDEN_DEATH, Bot, Casino,
                                 CasinoFly, ChoiceValues, Fear, Seat, barrel_image, board_image, likelier_higher,
                                 win_chance)
from tests.fakes import fake_components


def rigged(casino, cards, call=None):
    """Deal `cards` in order, and have the fly make `call(card)` -> (higher, big) each round
    (default: always a big bet on higher)."""
    deck = iter(cards)
    casino._deal = lambda: (next(deck), "S")

    def decide():
        higher, big = call(casino.table["card"]) if call else (True, True)
        casino.fly.choice = 0 if higher else 1
        return higher, big, (float(higher), float(big))
    casino.fly.decide = decide
    return casino


class TestRules(unittest.TestCase):
    def test_win_chances_and_the_likelier_side(self):
        self.assertAlmostEqual(win_chance(1, True), 12 / 13)
        self.assertEqual(win_chance(1, False), 0.0)          # nothing is lower than an ace
        self.assertAlmostEqual(win_chance(7, True), win_chance(7, False))
        self.assertTrue(likelier_higher(3))
        self.assertFalse(likelier_higher(11))

    def test_bets_pay_out_ties_lose_and_nobody_bets_more_than_they_have(self):
        seat = Seat("Fly #1")
        seat.place(higher=True, big=True, stake=2)
        self.assertEqual(seat.bet, 2 * BIG_BET)
        self.assertTrue(seat.settle(5, 9))
        self.assertEqual(seat.chips, START_CHIPS + 6)
        seat.place(higher=False, big=False, stake=1)
        self.assertFalse(seat.settle(8, 8))                  # a tie loses
        self.assertEqual(seat.chips, START_CHIPS + 5)
        seat.chips = 4
        seat.place(True, True, FINAL_STAKE)                  # a big bet at double stakes is 6: all in
        self.assertEqual(seat.bet, 4)
        seat.settle(13, 1)
        self.assertEqual(seat.chips, 0)
        self.assertTrue(seat.broke)

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

    def test_the_barrel_looms(self):
        bore = [float((barrel_image(t)[:, :, :3] < 8).all(axis=2).mean()) for t in (0.0, 0.5, 1.0)]
        self.assertLess(bore[0], 0.01)
        self.assertLess(bore[0], bore[1])
        self.assertLess(bore[1], bore[2])
        self.assertGreater(bore[2], 0.5)


class TestFear(unittest.TestCase):
    def setUp(self):
        self.c = fake_components()

    def test_danger_rises_as_the_end_nears_and_when_behind(self):
        fear = Fear(self.c, strength=1.0)
        calm = fear.assess(START_CHIPS, START_CHIPS, rnd=1, dread=0.1)
        self.assertLess(calm, 0.2)
        final = fear.assess(START_CHIPS, START_CHIPS, rnd=ROUNDS, stake=FINAL_STAKE, dread=0.1)
        self.assertGreater(final, calm)                                                     # the end is near
        self.assertGreater(fear.assess(4, START_CHIPS, rnd=1, dread=0.1), calm)             # behind
        self.assertGreater(fear.assess(START_CHIPS, START_CHIPS, rnd=1, dread=0.9), calm)   # expects to lose
        self.assertLess(fear.assess(16, START_CHIPS, rnd=ROUNDS, stake=FINAL_STAKE, dread=0.1), final)  # ahead
        self.assertEqual(Fear(self.c, strength=0).assess(0, 20, rnd=ROUNDS, dread=1.0), 0.0)  # fearless

    def test_terror_is_read_from_the_fear_circuit(self):
        fear = Fear(self.c)
        brain = self.c.brain
        for _ in range(10):
            fear.listen(brain.step())
        quiet = fear.terror
        fear.assess(0, 20, rnd=ROUNDS, stake=FINAL_STAKE, dread=1.0)
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

    def test_it_bets_big_when_confident_however_scared(self):
        fly = CasinoFly(fake_components(), {"fear": 1.0}, seed=0)
        fly.values.b[:] = (0.6, -0.6)                        # fairly sure "higher" wins
        for terror in (0.0, 1.0):
            fly.fear.terror = terror
            bets = [p_big for higher, _, (_, p_big) in (fly.decide() for _ in range(30)) if higher]
            self.assertGreater(np.mean(bets), 0.8)
        fly.values.b[:] = (0.1, -0.1)                        # only a hunch: small bets
        self.assertLess(max(fly.decide()[2][1] for _ in range(10)), 0.2)

    def test_a_loss_teaches_more_when_terrified(self):
        fly = CasinoFly(fake_components(), {"fear": 1.0}, seed=0, learn=False)
        fly.card_state = np.ones(fly.body.num_inputs, dtype=np.float32)
        fly.choice = 0
        self.assertLess(fly.outcome(False, terror_at_bet=1.0), fly.outcome(False, terror_at_bet=0.0))

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
    def casino(self, bot=None, dash=None):
        return Casino(fake_components(), {"fear": 1.0}, bot=bot, mode="fast", seed=0, dashboard=dash, verbose=False)

    def test_behind_after_three_rounds_gets_shot(self):
        from fly_jjs.core.dashboard import BrainDashboard
        c = fake_components()
        dash = BrainDashboard(c.brain)
        casino = Casino(c, {"fear": 1.0}, bot="pro", mode="fast", seed=0, dashboard=dash, verbose=False)
        # The fly always says lower, all in on big bets; the pro bot plays the odds.
        rigged(casino, [2, 13, 1, 5], call=lambda card: (False, True))
        self.assertEqual(casino.play_game(), "shot")           # 4 chips to the bot's 22
        table = dash.state()["casino"]
        self.assertEqual(table["target"], ["fly"])
        self.assertTrue(table["fly"]["shot"])
        self.assertEqual(table["banner"]["kind"], "dead")
        self.assertEqual((casino.deaths, casino.generation), (1, 2))
        self.assertEqual(casino.duels["bot"], 1)

    def test_a_fly_that_ends_ahead_lives(self):
        casino = rigged(self.casino(), [2, 13, 1, 5])          # +3, -3, then +6 at double stakes
        self.assertEqual(casino.play_game(), "survived")        # 16 chips beats the house's 10
        self.assertEqual((casino.deaths, casino.generation), (0, 1))

    def test_level_after_three_rounds_goes_to_sudden_death(self):
        casino = rigged(self.casino(), [2, 5, 9, 3, 12], call=lambda card: (True, False))
        self.assertEqual(casino.play_game(), "survived")        # 11, 12, 10: level; then 12
        self.assertEqual([h["round"] for h in casino.history], [1, 2, 3, 4])
        self.assertEqual(casino.history[-1]["fly"]["bet"], FINAL_STAKE)

    def test_still_level_after_sudden_death_is_a_draw(self):
        casino = self.casino(bot="pro")
        rigged(casino, [2, 5, 9, 3, 12, 4, 10, 1, 6], call=lambda card: casino.bot.decide(card))
        self.assertEqual(casino.play_game(), "draw")            # the fly copies the pro bot
        self.assertEqual(len(casino.history), ROUNDS + SUDDEN_DEATH)
        self.assertEqual((casino.deaths, casino.draws), (0, 1))

    def test_a_shot_fly_is_replaced_and_keeps_its_memory(self):
        casino = self.casino()
        casino.fly.values.b[:] = (-5.0, 5.0)                 # a fly sure that everything goes lower...
        casino.fly.values.w[:] = 0.0
        outcome = None
        for _ in range(20):
            outcome = casino.play_game()
            if outcome == "shot":
                break
        self.assertEqual(outcome, "shot")
        self.assertEqual(casino.deaths, 1)
        self.assertEqual(casino.generation, 2)
        self.assertTrue(casino.fly.fresh)                     # its brain settles before its first card
        steps = casino.steps
        casino.play_game()
        self.assertFalse(casino.fly.fresh)
        self.assertGreaterEqual(casino.steps - steps, 50)
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
        casino.play_game()
        state = dash.state()
        self.assertEqual(state["mode"], "casino")
        self.assertIn("terror", state["fear"])
        self.assertEqual(len(state["casino"]["strategy"]), RANKS)
        self.assertIn("Rookie", state["title"])
        table = state["casino"]
        self.assertEqual((table["start_chips"], table["big_bet"], table["rounds"]), (START_CHIPS, BIG_BET, ROUNDS))
        # The scoreboard's recent rounds: every bet settled the way the cards fell.
        played = [h["round"] for h in table["history"]]
        self.assertEqual(played, list(range(1, len(played) + 1)))
        self.assertGreaterEqual(len(played), 1)
        for h in table["history"]:
            for seat in (h["fly"], h["bot"]):
                higher = seat["choice"] == "higher"
                self.assertEqual(seat["won"], h["next"] > h["card"] if higher else h["next"] < h["card"])
                self.assertGreater(seat["bet"], 0)
        dash._pokes.append("stop")
        with self.assertRaises(StopCasino):
            casino.play_game()


if __name__ == "__main__":
    unittest.main()
