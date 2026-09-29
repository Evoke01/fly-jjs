"""The horse races: the fly bets on one of six horses and watches the race.

The races are totally random: every horse runs with the same speed, stamina and luck,
so each has the same one-in-six chance. The bookmaker does not know that. He prices
every race from made-up form, with a 25% margin on paper: someone picking at random
loses about 6% of what they bet, a favourite (short odds) is a terrible bet (about -47%),
and a long shot, priced as if it were hopeless, is a good one (about +59% for the longest
odds). Whether the fly works that out is up to it.

How the fly plays: it looks at the odds board (six rows, one bar per horse, longer for
longer odds) and bets on a horse, a large bet when it is confident. It learns what each
row is worth from dopamine after every race. Then it watches the race with its own eyes.
Its fear follows the race: a stake that is a big share of its money is frightening, and
more so the further its horse trails the leader as the finish nears. A long shot that
comes in (odds of 10 or more) is a jackpot. Broke means shot.
"""
import numpy as np
import cv2

from fly_jjs.core.casino import BOARD_H, BOARD_W, LOSS_AVERSION, PHASES, Table, _sigmoid, blank_image, utility
from fly_jjs.core.wallet import START_MONEY

HORSES = 6
TRACK = 320.0          # metres
SPEED = 17.0           # metres a second, before luck
GUST = 0.9             # how much a horse's pace wanders (m/s), and how fast (seconds)
GUST_TIME = 1.6
KICK = 1.4             # the most a horse finds for the last 40% of the race
BREAK = 0.35           # the slowest start out of the gate (seconds)
PULL_UP = 5.0          # m/s lost every second past the post
DT = 0.02              # one brain step
OVERROUND = 1.25       # the bookmaker's cut: his odds add up to 125%
FORM_SPREAD = 6.0      # how different the made-up form is (a Dirichlet concentration)
SMALL, LARGE = 50, 200
LARGE_EDGE = 0.2
LONG_SHOT = 10.0       # a winner at these odds or longer is a jackpot
TRACE_EVERY = 5        # positions sent to the page every 0.1 s

NAMES = ("Midnight Fly", "Buzz Kill", "Wing and a Prayer", "Swatted", "Compound Eye", "Fruit Loop", "Blue Bottle",
         "Fly by Night", "Sticky Paper", "Zapper", "Shoo-In", "Hoverboard", "Bug Juice", "Spider Bait",
         "Six Legs Fast", "Wingnut", "Proboscis", "Halteres", "Pupa Power", "Nectar Rush", "Window Pane",
         "Porch Light", "Rotten Banana", "Thorax")
SILKS = (("#c8352c", "#f4efe4"), ("#1f5aa6", "#f2c230"), ("#1f7a4d", "#f4efe4"), ("#1b1b1f", "#d9a521"),
         ("#6a3d9a", "#f4efe4"), ("#e0762b", "#1b1b1f"), ("#d86a9a", "#6f7780"), ("#f4efe4", "#c8352c"),
         ("#f2c230", "#1b1b1f"), ("#1f8a8a", "#f4efe4"), ("#7a2230", "#8fc1e8"), ("#3b3f46", "#e0762b"))
COATS = ("bay", "chestnut", "black", "grey", "dark bay", "palomino")
RACE_PHASES = {**PHASES, "board": (2, 50), "bet": (0, 50), "gates": (0, 60), "finish": (2, 70), "paid": (2, 50)}

LADDER = (1.4, 1.5, 1.6, 1.8, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0,
          13.0, 15.0, 17.0, 21.0, 26.0)


def price(rng, n=HORSES):
    """The bookmaker's odds (decimal: the stake comes back that many times) from made-up
    form. They add up to about OVERROUND, whatever the horses really are."""
    form = rng.dirichlet(np.full(n, FORM_SPREAD))
    raw = 1.0 / (form * OVERROUND)
    return [min(LADDER, key=lambda o: abs(np.log(o) - np.log(r))) for r in raw]


def run_race(rng, n=HORSES):
    """Run a totally random race. Returns (finish order, finish times, positions every
    DT until the last horse is home)."""
    break_at = rng.uniform(0.0, BREAK, n)
    kick = rng.uniform(0.0, KICK, n)
    gust = np.zeros(n)
    x = np.zeros(n)
    finish = np.full(n, np.inf)
    t = 0.0
    path = [x.copy()]
    while not np.all(np.isfinite(finish)):
        gust += -gust / GUST_TIME * DT + GUST * np.sqrt(2.0 * DT / GUST_TIME) * rng.standard_normal(n)
        late = np.clip((x / TRACK - 0.6) / 0.4, 0.0, 1.0)
        v = np.where(t >= break_at, SPEED + gust + kick * late, 0.0)
        done = np.isfinite(finish)
        v = np.where(done, np.maximum(4.0, v - PULL_UP * (t - np.where(done, finish, t))), v)   # past the post
        before = x.copy()
        x = x + np.maximum(v, 4.0 * (t >= break_at)) * DT
        crossed = (before < TRACK) & (x >= TRACK) & ~np.isfinite(finish)
        finish[crossed] = t + DT * (TRACK - before[crossed]) / (x[crossed] - before[crossed])
        t += DT
        path.append(x.copy())
    order = [int(i) for i in np.argsort(finish)]
    return order, finish, np.array(path)


def board_image(odds):
    """What the fly sees before the race: six rows, one per horse, each a bar as long as
    its odds are long (on a log scale, 1.4 to 26)."""
    img = blank_image()
    row = (BOARD_H - 8) // HORSES
    lo, hi = np.log(LADDER[0]), np.log(LADDER[-1])
    for i, o in enumerate(odds):
        y0 = 4 + i * row
        cv2.rectangle(img, (4, y0 + 2), (10, y0 + row - 3), (120, 120, 120, 255), -1)     # the row's number
        length = int(12 + (BOARD_W - 24) * (np.log(o) - lo) / (hi - lo))
        cv2.rectangle(img, (14, y0 + 3), (14 + length, y0 + row - 4), (235, 235, 235, 255), -1)
    return img


def race_image(x):
    """What the fly sees during the race: six lanes, each horse a bright blob."""
    img = blank_image()
    lane = (BOARD_H - 8) // HORSES
    cv2.line(img, (BOARD_W - 6, 2), (BOARD_W - 6, BOARD_H - 2), (90, 90, 96, 255), 1)     # the finish post
    for i, xi in enumerate(x):
        cy = 4 + i * lane + lane // 2
        cx = int(4 + (BOARD_W - 12) * min(xi, TRACK) / TRACK)
        cv2.ellipse(img, (cx, cy), (6, max(2, lane // 2 - 2)), 0, 0, 360, (240, 240, 240, 255), -1)
    return img


class RaceTable(Table):
    """The fly at the races. One game is one race."""

    game = "race"
    phases = RACE_PHASES
    CHOICES = tuple(f"horse {i + 1}" for i in range(HORSES))

    def __init__(self, components, cfg, **kw):
        super().__init__(components, cfg, **kw)
        self.mind = self.fly.mind("race", self.CHOICES)
        self.races = 0
        self.won = 0
        self.long_shots = 0
        self.staked = 0
        self.returned = 0
        self.shot_here = 0
        self.picks = []          # (odds rank of its pick: 0 = favourite, won) for the page
        self.card = []           # recent races, for the page

    def title(self):
        return f"Fly #{self.generation} at the races"

    def stats(self):
        return {"generation": self.generation, "games": self.games, "deaths": self.deaths, "races": self.races,
                "won": self.won, "long_shots": self.long_shots, "shot_here": self.shot_here,
                "return_pct": round(100 * self.returned / self.staked, 1) if self.staked else None,
                "picks": self.picks[-60:]}

    def extra(self):
        return {"card": list(self.card[-6:])}

    def play_game(self):
        self.banner = None
        names = [str(n) for n in self.rng.choice(NAMES, size=HORSES, replace=False)]
        silks = [list(SILKS[int(i)]) for i in self.rng.choice(len(SILKS), size=HORSES, replace=False)]
        coats = [str(c) for c in self.rng.choice(COATS, size=HORSES)]
        odds = price(self.rng)
        horses = [{"n": i + 1, "name": names[i], "silks": silks[i], "coat": coats[i], "odds": odds[i]}
                  for i in range(HORSES)]
        start = self.wallet.money
        base = {"number": self.games + 1, "horses": horses, "pick": None, "stake": 0, "race": None, "result": None,
                "fly": {"name": f"Fly #{self.generation}", "shot": False}, "target": None}
        self._wake(**base)
        self.table.update(base, phase="board")
        view = board_image(odds)
        self._show(view)
        self._run("board", view)

        # It reads the odds, and bets.
        self.fly.fear.feel(0.2 * float(np.clip(1.0 - start / START_MONEY, 0.0, 1.0)))
        self.table.update(phase="think")
        self._run("think", view)
        self.mind.perceive(self.fly.look())
        q, p = self.mind.probs()
        pick = int(self.rng.choice(HORSES, p=p))
        p_large = float(_sigmoid(8.0 * (q[pick] - LARGE_EDGE)))
        stake = min(LARGE if self.rng.random() < p_large else SMALL, self.wallet.money)
        at_risk = stake / max(self.wallet.money, 1)
        self.fly.fear.feel(0.5 * at_risk + 0.3 * float(np.clip(1.0 - start / START_MONEY, 0.0, 1.0)))
        self._run("fear", view)
        terror = self.fly.fear.terror
        self.wallet.change(-stake, f"Races: ${stake} on #{pick + 1} {names[pick]} at {odds[pick]:g}")
        self.staked += stake
        self.table.update(phase="bet", pick=pick, stake=stake, decision={"p": [round(float(v), 3) for v in p],
                                                                         "p_large": round(p_large, 3)})
        self._say(f"Fly #{self.generation} bets ${stake} on #{pick + 1} {names[pick]} at {odds[pick]:g}.")
        self._run("bet", view)

        # The race itself: totally random.
        order, finish, path = run_race(self.rng)
        trace = path[::TRACE_EVERY]
        self.table.update(phase="gates", race={"track": TRACK, "every": DT * TRACE_EVERY,
                                               "x": [[round(float(v), 2) for v in row] for row in trace.T],
                                               "finish": [round(float(t), 3) for t in finish]})
        self._run("gates", race_image(path[0]))
        self.table.update(phase="race")
        steps = len(path) if not self.fast else 16
        frames = path if not self.fast else path[np.linspace(0, len(path) - 1, steps).astype(int)]
        stake_fear = 0.5 * at_risk

        def watch(t):
            k = min(int(round(t * (steps - 1))), steps - 1)
            x = frames[k]
            progress = float(np.clip(x.max() / TRACK, 0.0, 1.0))
            gap = float(np.clip((x.max() - x[pick]) / 12.0, 0.0, 1.0))
            self.fly.fear.feel(stake_fear + 0.6 * gap * progress)
            self.table["race_t"] = round(k * (DT if not self.fast else DT * (len(path) - 1) / (steps - 1)), 2)
            return race_image(x)
        self._run("race", watch, steps=steps)

        won = order[0] == pick
        paid = int(round(stake * odds[pick])) if won else 0
        self.races += 1
        rank = sorted(range(HORSES), key=lambda i: odds[i]).index(pick)
        self.picks.append([rank, bool(won)])
        if won:
            self.won += 1
            self.returned += paid
            self.wallet.change(paid, f"Races: #{pick + 1} {names[pick]} won at {odds[pick]:g}")
        net = (paid - stake) / stake if stake else 0.0
        target = utility(net) * (1.0 + (LOSS_AVERSION * terror * self.fly.fear.strength if net < 0 else 0.0))
        dopamine = self.mind.learn(pick, target, learn=self.fly.learn)
        photo = bool(finish[order[1]] - finish[order[0]] < 0.05)
        result = {"order": order, "won": bool(won), "paid": paid, "photo": photo,
                  "margin": round(float((finish[order[1]] - finish[order[0]]) * SPEED), 2)}
        self.card.append({"winner": order[0] + 1, "name": names[order[0]], "odds": odds[order[0]],
                          "pick": pick + 1, "stake": stake, "paid": paid})
        self.fly.fear.danger = 0.0
        self.table.update(phase="finish", result=result)
        self._say(f"#{order[0] + 1} {names[order[0]]} wins at {odds[order[0]]:g}"
                  + (" in a photo finish" if photo else "") + (f". Fly #{self.generation} collects ${paid:,}."
                                                              if won else f". Fly #{self.generation} loses ${stake}."))
        self._run("finish", race_image(path[-1]), dopamine=dopamine)
        if won and odds[pick] >= LONG_SHOT:
            self.long_shots += 1
            self._jackpot(f"#{pick + 1} {names[pick]} came in at {odds[pick]:g}! Fly #{self.generation} wins ${paid:,}.",
                          dopamine=1.0)
            self.banner = None
        else:
            self.table.update(phase="paid")
            self._run("paid", race_image(path[-1]))
        return self._finish(start)

    def _finish(self, start):
        self.games += 1
        outcome = "won" if self.card[-1]["paid"] else "lost"
        if self.wallet.broke:
            why = f"Fly #{self.generation} is broke: it bet its last ${self.card[-1]['stake']:,} and lost"
            if self._execute(["fly"], why):
                self.shot_here += 1
            outcome = "shot"
        self.wallet.end_game()
        if self.verbose:
            s = self.stats()
            print(f"[Races] Race {self.races}: {outcome.upper():5s} | ${start:,} -> ${self.wallet.money:,} | "
                  f"won {self.won} of {self.races} | returned {s['return_pct']}% of stakes | flies shot {self.deaths}")
        return outcome
