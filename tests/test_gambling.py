"""Money, the slot machine, the horse races, and playing one game at a time."""
import json
import os
import tempfile
import unittest
import urllib.error
import urllib.request

import numpy as np

import fly_jjs.core.race as race
import fly_jjs.core.slots as slots
from fly_jjs.core.casino import CHIP_VALUE, START_CHIPS, Casino, CasinoFly, make_table
from fly_jjs.core.dashboard import BrainDashboard
from fly_jjs.core.wallet import START_MONEY, Wallet
from tests.fakes import FakeBrain, fake_components


def table(game, wallet=None, dash=None, seed=0, session=None, fear=1.0):
    c = fake_components()
    fly = CasinoFly(c, {"fear": fear}, seed=seed)
    return make_table(game, c, {"fear": fear}, fly, wallet or Wallet(), session if session is not None else {},
                      mode="fast", seed=seed, dashboard=dash, verbose=False)


class TestWallet(unittest.TestCase):
    def test_nobody_pays_more_than_they_have(self):
        w = Wallet()
        self.assertEqual(w.change(-300, "bet"), -300)
        self.assertEqual(w.change(-5000, "all in"), -(START_MONEY - 300))
        self.assertTrue(w.broke)
        self.assertEqual(w.house, START_MONEY)

    def test_a_shot_fly_leaves_its_money_to_the_house(self):
        w = Wallet()
        w.change(500, "jackpot")
        self.assertEqual(w.richest, {"fly": 1, "money": START_MONEY + 500})
        w.died()
        self.assertEqual((w.generation, w.money, w.deaths), (2, START_MONEY, 1))
        self.assertEqual(w.richest["fly"], 1)                  # the record stays

    def test_saved_between_runs(self):
        path = os.path.join(tempfile.mkdtemp(), "wallet.json")
        w = Wallet(path)
        w.change(-250, "bet")
        w.end_game()
        again = Wallet(path)
        self.assertEqual((again.money, again.games, list(again.history)), (START_MONEY - 250, 1, [START_MONEY, 750]))
        with open(path, "w") as f:
            f.write("not json")
        self.assertEqual(Wallet(path).money, START_MONEY)       # a broken file starts fresh


class TestDeathMatchMoney(unittest.TestCase):
    def test_chips_are_bought_and_cashed_out(self):
        w = Wallet()
        casino = Casino(fake_components(), {"fear": 1.0}, bot=None, mode="fast", seed=0, verbose=False, wallet=w)
        deck = iter([2, 13, 1, 5])
        casino._deal = lambda: (next(deck), "S")

        def decide():
            casino.fly.choice = 0
            return True, True, (1.0, 1.0)
        casino.fly.decide = decide
        self.assertEqual(casino.play_game(), "survived")       # 16 chips: +3, -3, +6
        self.assertEqual(w.money, START_MONEY - START_CHIPS * CHIP_VALUE + 16 * CHIP_VALUE)

    def test_a_broke_fly_is_shot_before_it_plays(self):
        w = Wallet()
        w.change(-(START_MONEY - 5), "lost it all")
        casino = Casino(fake_components(), {"fear": 1.0}, bot="rookie", mode="fast", seed=0, verbose=False, wallet=w)
        self.assertEqual(casino.play_game(), "shot")
        self.assertEqual((w.generation, w.money, casino.rounds), (2, START_MONEY, 0))


class TestSlots(unittest.TestCase):
    def test_the_machine_keeps_eight_percent(self):
        self.assertAlmostEqual(slots.payback(), 0.92, delta=0.005)
        self.assertEqual(slots.pays(("SEVEN", "SEVEN", "SEVEN")), (30, "JACKPOT"))
        self.assertEqual(slots.pays(("SEVEN", "BAR", "SEVEN"))[0], slots.TWO_SEVENS)
        self.assertEqual(slots.pays(("LEMON", "CHERRY", "CHERRY"))[0], slots.TWO_CHERRIES)
        self.assertEqual(slots.pays(("LEMON", "BAR", "BELL")), (0, ""))
        rng = np.random.default_rng(0)
        spun = [slots.spin_reels(rng) for _ in range(20000)]
        paid = np.mean([slots.pays(r)[0] for r in spun])
        self.assertAlmostEqual(paid, 0.92, delta=0.05)

    def test_it_sees_the_reels(self):
        still = slots.machine_image(("SEVEN", "BAR", "LEMON"))
        blur = slots.machine_image(("SEVEN", "BAR", "LEMON"), spinning=(True, True, True), t=0.3)
        self.assertEqual(still.shape, blur.shape)
        self.assertGreater(np.abs(still.astype(int) - blur.astype(int)).sum(), 0)

    def test_a_jackpot_pays_thirty_times(self):
        t = table("slots")
        t._decide = lambda n: (n < 1, slots.SMALL, (1.0, 0.0))            # one spin, then it walks
        t.fly.learn = True
        orig = slots.spin_reels
        slots.spin_reels = lambda rng: ("SEVEN", "SEVEN", "SEVEN")
        try:
            self.assertEqual(t.play_game(), "walked")
        finally:
            slots.spin_reels = orig
        self.assertEqual(t.wallet.money, START_MONEY - slots.SMALL + 30 * slots.SMALL)
        self.assertEqual(t.jackpots, 1)
        self.assertGreater(float(t.mind.values.b[0]), 0.0)                 # spinning looks good now

    def test_it_walks_away_or_goes_broke(self):
        t = table("slots")
        t.fly.fear.strength = 0.0
        t._decide = lambda n: (True, slots.LARGE, (1.0, 1.0))              # never stops
        orig = slots.spin_reels
        slots.spin_reels = lambda rng: ("LEMON", "BAR", "BELL")
        try:
            t.wallet.change(-(START_MONEY - 120), "a bad week")
            self.assertEqual(t.play_game(), "shot")                        # 50, 50, then its last 20
        finally:
            slots.spin_reels = orig
        self.assertEqual((t.wallet.generation, t.wallet.money), (2, START_MONEY))
        self.assertEqual(len(t.visit), 3)

    def test_fear_pulls_it_off_the_machine(self):
        t = table("slots")
        t.fly.fear.terror = 0.0
        calm = np.mean([t._decide(slots.MIN_SPINS)[2][0] for _ in range(3)])
        t.fly.fear.terror = 1.0
        scared = np.mean([t._decide(slots.MIN_SPINS)[2][0] for _ in range(3)])
        self.assertGreater(calm, scared + 0.3)
        self.assertTrue(t._decide(0)[0])                                   # the first spins are compulsory

    def test_visits_on_the_fake_brain(self):
        t = table("slots", seed=3)
        outcomes = [t.play_game() for _ in range(4)]
        self.assertTrue(set(outcomes) <= {"walked", "shot"})
        self.assertGreaterEqual(t.spins, 4 * slots.MIN_SPINS)


class TestRaces(unittest.TestCase):
    def test_the_bookmaker_prices_every_race(self):
        rng = np.random.default_rng(0)
        for _ in range(50):
            odds = race.price(rng)
            self.assertEqual(len(odds), race.HORSES)
            self.assertTrue(all(o in race.LADDER for o in odds))
            self.assertAlmostEqual(sum(1 / o for o in odds), race.OVERROUND, delta=0.12)

    def test_the_races_are_totally_random(self):
        rng = np.random.default_rng(1)
        wins = np.zeros(race.HORSES)
        for _ in range(600):
            order, finish, path = race.run_race(rng)
            wins[order[0]] += 1
            self.assertEqual(sorted(order), list(range(race.HORSES)))
            self.assertTrue(np.all(np.diff(finish[order]) >= 0))
            self.assertTrue(np.all(path[-1] >= race.TRACK))
        self.assertLess(np.abs(wins / 600 - 1 / race.HORSES).max(), 0.06)   # each horse about 1 in 6

    def test_it_sees_the_board_and_the_race(self):
        a = race.board_image([2.0, 3.0, 5.0, 8.0, 13.0, 21.0])
        b = race.board_image([21.0, 13.0, 8.0, 5.0, 3.0, 2.0])
        self.assertGreater(np.abs(a.astype(int) - b.astype(int)).sum(), 0)
        self.assertEqual(race.race_image(np.full(race.HORSES, 100.0)).shape, a.shape)

    def rigged(self, t, winner, pick, odds):
        t.mind.probs = lambda *a, **k: (np.zeros(race.HORSES), np.eye(race.HORSES)[pick])
        race_price, race_run = race.price, race.run_race
        race.price = lambda rng, n=race.HORSES: list(odds)

        def run(rng, n=race.HORSES):
            order, finish, path = race_run(rng, n)
            order = [winner] + [i for i in order if i != winner]
            finish = np.sort(finish)[np.argsort(order)]
            return order, finish, path
        race.run_race = run
        return race_price, race_run

    def test_a_winner_pays_the_odds_and_a_long_shot_is_a_jackpot(self):
        dash = BrainDashboard(FakeBrain())
        t = table("race", dash=dash)
        saved = self.rigged(t, winner=2, pick=2, odds=[2.0, 3.0, 13.0, 5.0, 6.0, 8.0])
        try:
            self.assertEqual(t.play_game(), "won")
        finally:
            race.price, race.run_race = saved
        stake = t.card[-1]["stake"]
        self.assertEqual(t.wallet.money, START_MONEY - stake + 13 * stake)
        self.assertEqual(t.long_shots, 1)
        state = dash.state()["casino"]
        self.assertEqual(state["game"], "race")
        self.assertEqual(len(state["race"]["x"]), race.HORSES)
        self.assertEqual(state["result"]["order"][0], 2)

    def test_broke_at_the_races_is_shot(self):
        t = table("race")
        t.wallet.change(-(START_MONEY - 30), "a bad month")
        saved = self.rigged(t, winner=0, pick=5, odds=[2.0, 3.0, 13.0, 5.0, 6.0, 8.0])
        try:
            self.assertEqual(t.play_game(), "shot")
        finally:
            race.price, race.run_race = saved
        self.assertEqual((t.wallet.generation, t.wallet.money), (2, START_MONEY))


class TestOneGameAtATime(unittest.TestCase):
    def test_the_page_picks_what_is_next(self):
        dash = BrainDashboard(FakeBrain())
        session = {"loop": False}
        t = table("cards", dash=dash, session=session)
        dash._pokes.extend(["slots"])
        self.assertEqual(t.wait(), "slots")
        self.assertFalse(session["waiting"])
        dash._pokes.extend(["loop"])
        self.assertEqual(t.wait(), "again")                   # looping: straight on
        self.assertTrue(session["loop"])
        dash._pokes.extend(["stop"])
        from fly_jjs.core.casino import StopCasino
        session["loop"] = False
        with self.assertRaises(StopCasino):
            t.wait()

    def test_run_casino_plays_one_game_then_waits(self):
        import fly_jjs.core.brain as brain
        import fly_jjs.core.casino as casino
        played = []
        orig_components, orig_wait = brain.get_brain_components, casino.Table.wait
        brain.get_brain_components = fake_components
        waits = iter(["race", "again"])

        def wait(self):
            played.append(self.game)
            try:
                return next(waits)
            except StopIteration:
                raise casino.StopCasino
        casino.Table.wait = wait
        d = tempfile.mkdtemp()
        try:
            last = casino.run_casino(game="slots", mode="show", dashboard=False, fear=1.0, seed=0, verbose=False,
                                     memory_path=os.path.join(d, "m.npz"), money_path=os.path.join(d, "w.json"),
                                     loop=False)
        finally:
            brain.get_brain_components, casino.Table.wait = orig_components, orig_wait
        self.assertEqual(played, ["slots", "race", "race"])    # slots, then the page asked for the races twice
        self.assertEqual(last.game, "race")
        with open(os.path.join(d, "w.json")) as f:
            self.assertEqual(json.load(f)["games"], 3)
        saved = np.load(os.path.join(d, "m.npz"))
        self.assertIn("slots_w", saved.files)
        self.assertIn("race_w", saved.files)


class TestMemory(unittest.TestCase):
    def test_every_game_is_remembered_and_old_files_still_load(self):
        c = fake_components()
        fly = CasinoFly(c, {}, seed=0)
        fly.values.b[:] = (0.25, -0.5)
        fly.mind("slots", slots.SlotTable.CHOICES).values.b[:] = (-0.3, 0.0)
        path = os.path.join(tempfile.mkdtemp(), "casino_memory.npz")
        fly.save(path)
        again = CasinoFly(c, {}, seed=0)
        self.assertTrue(again.load(path))
        np.testing.assert_allclose(again.values.b, (0.25, -0.5))
        np.testing.assert_allclose(again.minds["slots"].values.b, (-0.3, 0.0))
        old = os.path.join(os.path.dirname(path), "old.npz")
        np.savez(old, w=fly.values.w, b=fly.values.b, looks=7, usual=np.zeros(0, np.float32))
        older = CasinoFly(c, {}, seed=0)
        self.assertTrue(older.load(old))
        np.testing.assert_allclose(older.values.b, (0.25, -0.5))
        self.assertEqual(older.looks, 7)


class TestStaticFiles(unittest.TestCase):
    def test_the_page_gets_its_scripts_and_sounds_and_nothing_else(self):
        dash = BrainDashboard(FakeBrain(), port=18777)
        url = dash.start(open_browser=False)
        try:
            def get(path):
                try:
                    with urllib.request.urlopen(url + path, timeout=5) as r:
                        return r.status, r.headers.get("Content-Type"), r.read()
                except urllib.error.HTTPError as e:
                    return e.code, None, b""
            status, kind, body = get("web/vendor/three.module.min.js")
            self.assertEqual((status, kind.split(";")[0]), (200, "text/javascript"))
            self.assertIn(b"three.js", body[-400:].lower().replace(b"three.js authors", b"three.js"))
            self.assertEqual(get("web/sounds/shot.mp3")[:2], (200, "audio/mpeg"))
            self.assertEqual(get("web/sounds/jackpot.mp3")[0], 200)
            self.assertEqual(get("web/casino3d.js")[0], 200)
            self.assertEqual(get("web/../core/casino.py")[0], 404)
            self.assertEqual(get("web/%2e%2e/core/wallet.py")[0], 404)
            self.assertEqual(get("web/brain3d.html")[0], 404)
            self.assertEqual(get("web/nope.js")[0], 404)
        finally:
            dash.stop()


if __name__ == "__main__":
    unittest.main()
