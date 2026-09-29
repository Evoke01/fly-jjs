"""The slot machine: the fly pulls the lever, or walks away with what it has left.

Three reels of five symbols. Three of a kind pays (7-7-7 is the jackpot, 30 times the
bet), and so do two sevens or two cherries. The machine keeps 8% of what goes in: every
spin loses a little on average, and 7-7-7 comes up about once in 140 spins.

How the fly plays: it looks at the machine (the reels still showing its last spin) and
chooses to spin again or to walk away, and how much to bet. Two things pull on it. The
thrill of the game, plus the value of spinning it has learned (after every spin dopamine
moves that value toward what the spin paid, felt on a log scale), pull it to the lever.
Fear, read from its fear circuit and driven by how much of its money has drained away,
pulls it off: a scared fly walks away. A fearless fly keeps spinning until it is broke,
and broke means shot. The house makes it pull at least three times.
"""
import numpy as np
import cv2

from fly_jjs.core.casino import BOARD_H, BOARD_W, LOSS_AVERSION, PHASES, Table, _sigmoid, blank_image, utility
from fly_jjs.core.wallet import START_MONEY

SYMBOLS = ("SEVEN", "BAR", "BELL", "CHERRY", "LEMON")
REEL = {"SEVEN": 5, "BAR": 5, "BELL": 4, "CHERRY": 4, "LEMON": 8}     # stops on each reel
THREE = {"SEVEN": 30, "BAR": 15, "BELL": 10, "CHERRY": 8, "LEMON": 5}   # three of a kind pays this many bets
TWO_SEVENS = 3
TWO_CHERRIES = 2
SMALL, LARGE = 10, 50       # dollars a spin
MIN_SPINS, MAX_SPINS = 3, 25
THRILL = 0.5                # how much the fly likes pulling the lever, in value units
FEAR_BRAKE = 1.0            # full terror takes this much off
LARGE_EDGE = 0.3            # bets large when it has learned that spinning pays this well

# Watching: the reels stop one after another; with two sevens up, the last one spins on
# (the "reach"). Steps of 20 ms.
REEL_STOPS = (1.0, 1.5, 2.0)
REACH_STOP = 3.3
SETTLE = 0.4                # and the spin goes on this long after the last one stops
SLOT_PHASES = {**PHASES, "pull": (0, 15), "paid": (2, 45), "walk": (2, 90)}


def pays(reels):
    """How many bets a spin pays (0 for a loss), and its name."""
    a, b, c = reels
    if a == b == c:
        return THREE[a], ("JACKPOT" if a == "SEVEN" else f"three {a.lower()}s")
    if reels.count("SEVEN") == 2:
        return TWO_SEVENS, "two sevens"
    if reels.count("CHERRY") == 2:
        return TWO_CHERRIES, "two cherries"
    return 0, ""


def payback():
    """What the machine pays back, on average, for every dollar that goes in."""
    total = sum(REEL.values())
    p = {s: n / total for s, n in REEL.items()}
    out = 0.0
    for a in SYMBOLS:
        for b in SYMBOLS:
            for c in SYMBOLS:
                out += p[a] * p[b] * p[c] * pays((a, b, c))[0]
    return out


def spin_reels(rng):
    total = sum(REEL.values())
    return tuple(str(s) for s in rng.choice(SYMBOLS, size=3, p=[REEL[s] / total for s in SYMBOLS]))


def _draw_symbol(img, symbol, x0, y0, w, h, colour=(235, 235, 235, 255)):
    cx, cy = x0 + w // 2, y0 + h // 2
    if symbol == "SEVEN":
        cv2.line(img, (x0 + 8, y0 + 12), (x0 + w - 8, y0 + 12), colour, 4)
        cv2.line(img, (x0 + w - 8, y0 + 12), (cx - 4, y0 + h - 10), colour, 4)
    elif symbol == "BAR":
        for dy in (-12, 0, 12):
            cv2.rectangle(img, (x0 + 8, cy + dy - 3), (x0 + w - 8, cy + dy + 3), colour, -1)
    elif symbol == "BELL":
        cv2.ellipse(img, (cx, cy + 6), (w // 3, h // 3), 0, 180, 360, colour, -1)
        cv2.rectangle(img, (x0 + 8, cy + 6), (x0 + w - 8, cy + 10), colour, -1)
    elif symbol == "CHERRY":
        cv2.circle(img, (cx - 8, cy + 8), 7, colour, -1)
        cv2.circle(img, (cx + 8, cy + 8), 7, colour, -1)
        cv2.line(img, (cx - 8, cy + 2), (cx + 4, y0 + 10), colour, 2)
        cv2.line(img, (cx + 8, cy + 2), (cx + 4, y0 + 10), colour, 2)
    elif symbol == "LEMON":
        cv2.ellipse(img, (cx, cy), (w // 3, h // 5), 0, 0, 360, colour, -1)


def machine_image(reels=None, spinning=(False, False, False), t=0.0):
    """What the fly sees: the machine's three reel windows. A spinning reel is a blur of
    stripes running past; a stopped one shows its symbol."""
    img = blank_image()
    w, h = 56, 72
    gap = (BOARD_W - 3 * w) // 4
    for i in range(3):
        x0, y0 = gap + i * (w + gap), (BOARD_H - h) // 2
        cv2.rectangle(img, (x0 - 2, y0 - 2), (x0 + w + 2, y0 + h + 2), (90, 90, 96, 255), 1)
        if spinning[i]:
            offset = int(t * 900 + i * 17) % 12
            for y in range(y0 - 12 + offset, y0 + h, 12):
                cv2.rectangle(img, (x0 + 4, max(y0, y)), (x0 + w - 4, min(y0 + h, y + 5)), (150, 150, 150, 255), -1)
        elif reels is not None:
            _draw_symbol(img, reels[i], x0, y0, w, h)
    return img


class SlotTable(Table):
    """The fly at the slot machine. One game is one visit: it plays until it walks away,
    goes broke, or has pulled the lever MAX_SPINS times."""

    game = "slots"
    phases = SLOT_PHASES
    CHOICES = ("spin", "walk")

    def __init__(self, components, cfg, **kw):
        super().__init__(components, cfg, **kw)
        self.mind = self.fly.mind("slots", self.CHOICES)
        self.last = None               # what the reels show
        self.spins = 0                 # all visits
        self.jackpots = 0
        self.wagered = 0
        self.paid_out = 0
        self.walked = 0
        self.shot_here = 0
        self.visit = []                # this visit's spins, for the page

    def title(self):
        return f"Fly #{self.generation} at the slot machine"

    def stats(self):
        return {"generation": self.generation, "games": self.games, "deaths": self.deaths, "spins": self.spins,
                "jackpots": self.jackpots, "walked": self.walked, "shot_here": self.shot_here,
                "payback_pct": round(100 * self.paid_out / self.wagered, 1) if self.wagered else None,
                "machine_pct": round(100 * payback(), 1)}

    def extra(self):
        q, _ = self.mind.probs()
        return {"visit": list(self.visit[-12:]), "value": {"spin": round(float(q[0]), 3), "walk": round(float(q[1]), 3),
                                                             "thrill": THRILL}}

    def _danger(self, start, dread):
        """How much danger the fly is in: how much of the money it walked in with has
        drained away (a third gone is the most), how close to broke it is overall, and how
        badly it expects the next spin to go."""
        money = self.wallet.money
        drained = float(np.clip((start - money) / max(start / 3.0, 1.0), 0.0, 1.0))
        poor = float(np.clip(1.0 - money / START_MONEY, 0.0, 1.0))
        expected_loss = float(np.clip((dread - 0.2) / 0.8, 0.0, 1.0))
        return 0.6 * drained + 0.4 * poor + 0.2 * expected_loss

    def _decide(self, spins_so_far):
        """(spin?, bet, (p_spin, p_large)) from the learned values, the thrill and fear."""
        fear = self.fly.fear
        pull = THRILL - FEAR_BRAKE * fear.terror * fear.strength
        q, p = self.mind.probs(bias=[pull, 0.0])
        spin = spins_so_far < MIN_SPINS or bool(self.rng.random() < p[0])
        p_large = float(_sigmoid(8.0 * (q[0] - LARGE_EDGE)))      # the thrill makes it play, not bet big
        large = bool(self.rng.random() < p_large)
        bet = min(LARGE if large else SMALL, self.wallet.money)
        return spin, bet, (float(p[0]), p_large)

    def play_game(self):
        self.banner = None
        self.visit = []
        start = self.wallet.money
        base = {"number": self.games + 1, "spin": None, "reels": self.last, "start_money": start,
                "fly": {"name": f"Fly #{self.generation}", "shot": False}, "target": None}
        self._wake(**base)
        self.table.update(base)
        outcome = None
        n = 0
        while n < MAX_SPINS:
            if self.wallet.broke:
                outcome = "shot"
                break
            view = machine_image(self.last)
            self._show(view)
            q, _ = self.mind.probs()
            dread = float(np.clip((1.0 - np.clip(q[0], -1.0, 1.0)) / 2.0, 0.0, 1.0))
            self.fly.fear.feel(self._danger(start, dread))
            self.table.update(phase="think", target=None)
            self._run("think", view)
            self.mind.perceive(self.fly.look())
            self._run("fear", view)
            spin, bet, probs = self._decide(n)
            self.table.update(decision={"p_spin": round(probs[0], 3), "p_large": round(probs[1], 3)})
            if not spin:
                self.mind.learn(1, 0.0, learn=self.fly.learn)
                self.walked += 1
                outcome = "walked"
                break
            terror = self.fly.fear.terror
            n += 1
            self.spins += 1
            self.wagered += bet
            self.wallet.change(-bet, f"Slots: spin {n}")
            self.table.update(phase="pull", bet=bet)
            self._run("pull", view)

            reels = spin_reels(self.rng)
            times, reach = self._timing(reels)
            multiple, name = pays(reels)
            win = bet * multiple
            self.table.update(phase="spin", spin={"n": n, "reels": list(reels), "stops": list(times), "reach": reach,
                                                  "bet": bet, "win": win, "name": name})
            self._run("spin", self._spinning(reels, times), steps=self._spin_steps(times))
            self.last = reels
            if win:
                self.paid_out += win
                self.wallet.change(win, f"Slots: {name}")
            net = (win - bet) / bet
            target = utility(net) * (1.0 + (LOSS_AVERSION * terror * self.fly.fear.strength if net < 0 else 0.0))
            dopamine = self.mind.learn(0, target, learn=self.fly.learn)
            self.visit.append({"n": n, "reels": list(reels), "bet": bet, "win": win, "name": name})
            self._say(f"Fly #{self.generation}: ${bet} spin, {' '.join(r.lower() for r in reels)}"
                      + (f": {name}, won ${win}" if win else "") + f". ${self.wallet.money}.")
            self.table.update(phase="paid", reels=list(reels))
            if name == "JACKPOT":
                self.jackpots += 1
                self._jackpot(f"7-7-7! Fly #{self.generation} wins ${win:,} on a ${bet} spin.", dopamine=1.0)
                self.banner = None
            else:
                self._run("paid", machine_image(reels), dopamine=dopamine)
        else:
            outcome = "walked"
        return self._finish(outcome, start)

    def _timing(self, reels):
        reach = reels[0] == reels[1] == "SEVEN"
        return (REEL_STOPS[0], REEL_STOPS[1], REACH_STOP if reach else REEL_STOPS[2]), reach

    def _spin_steps(self, times):
        return 3 if self.fast else int(round((times[-1] + SETTLE) / 0.02))

    def _spinning(self, reels, times):
        """The reels as the fly sees them over the spin (t from 0 to 1 of the phase)."""
        total = times[-1] + SETTLE

        def frame(t):
            now = t * total
            return machine_image(reels, spinning=tuple(now < stop for stop in times), t=now)
        return frame

    def _finish(self, outcome, start):
        self.games += 1
        money = self.wallet.money
        name = f"Fly #{self.generation}"
        if outcome == "shot":
            why = f"{name} is broke: it lost ${start:,} at the slot machine"
            if self._execute(["fly"], why):
                self.shot_here += 1
        else:
            change = money - start
            self.banner = {"kind": "good" if change > 0 else "neutral", "title": "Walked away",
                           "detail": f"{name} leaves the machine with ${money:,} "
                                     f"({'+' if change >= 0 else '-'}${abs(change):,} after {len(self.visit)} spins)."}
            self._say(self.banner["detail"])
            self.fly.fear.danger = 0.0
            self.table.update(phase="walk")
            self._run("walk", machine_image(self.last))
        self.wallet.end_game()
        if self.verbose:
            s = self.stats()
            print(f"[Slots] Visit {self.games}: {outcome.upper():6s} | {len(self.visit)} spins | ${start:,} -> "
                  f"${self.wallet.money:,} | machine paid back {s['payback_pct']}% | jackpots {self.jackpots} | "
                  f"flies shot {self.deaths}")
        return outcome
