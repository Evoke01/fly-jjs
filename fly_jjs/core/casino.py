"""The casino: a death match at Higher or Lower. Whoever loses gets shot.

A card is dealt; each player says whether the next card will be higher or lower and
bets chips on it (ties lose). Win and you gain what you bet, lose and you lose it. A
game is three rounds, the last for double stakes. Then whoever has fewer chips is shot;
if they are level, sudden-death rounds decide it. Run out of chips and you are shot on
the spot. Alone at the table the fly plays the house: it is shot if it ends the game
with fewer chips than it started with, and walks free with more.

How the fly plays
-----------------
* It sees the table with its own eyes: the dealt card lights up on a board of 13
  slots, ace on the far left and king on the far right, the way flies are shown bars
  in lab arenas. It looks for 0.4 s; its readout neurons (about 59,000), averaged over
  that look and taken relative to its usual state, are what it knows about the card.
* It learns what each choice is worth for the card in view: one value for "higher" and
  one for "lower". After every round the chosen value moves toward what happened, in
  proportion to the surprise (delta = outcome - expected): the dopamine signal. It is
  sent back into the brain as reward (PAM neurons) or punishment (PPL1) dopamine.
* It picks the side it values more (mostly), and bets big when it is confident the
  side will win.
* It is afraid. Danger (how near the end of the game is, how far behind it is, and how
  likely it thinks it is to lose on this card) drives its real fear circuit: the LC4
  and LPLC2 threat and looming detectors and the PPL1 punishment neurons. The
  connectome carries that on to the giant fibre (DNp01), the neuron that fires the
  escape jump. The terror meter is how hard that circuit fires: measured, not made up.
  The more terrified it was when it bet, the more a loss teaches it. (Terror does not
  make it bet small: in a death match holding back only gets you shot.)
* About to be shot, it sees the gun barrel coming at it: a looming dark disk, the
  stimulus its looming detectors and giant fibre respond to. Once shot, its brain is no
  longer run and falls silent. The next fly takes its seat; it keeps what the others
  learned, and its brain activity starts fresh.

This is a simulation of a connectome; "fear" here is the activity of the neurons that
fire when real flies escape threats, not a claim about what a fly feels.
"""
import os
import time
from collections import deque

import numpy as np
import cv2

RANKS = 13
RANK_NAMES = ("", "A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
SUITS = "SHDC"
START_CHIPS = 10
BIG_BET = 3          # a big bet risks three times the stake
ROUNDS = 3           # rounds in a game; then whoever is behind is shot
FINAL_STAKE = 2      # the last round, and sudden death, are for double stakes
SUDDEN_DEATH = 5     # still level after this many extra rounds: a draw, nobody is shot

# The fly's eye view: 13 slots, ace on the far left and king on the far right.
BOARD_W, BOARD_H = 208, 104

# Learning. Replaying recorded brain states offline: learning on the raw state got
# nowhere (most activity is the same for every card), and an actor-critic sometimes
# locked into the wrong side for good; values per choice with normalised steps reached
# 86-94% smart picks within ~200 rounds on every seed tried.
VALUE_LR = 0.3       # normalised LMS step (stable for anything below 2)
BIAS_LR = 0.05
USUAL_RATE = 0.02    # the fly's usual brain state is followed over ~50 rounds
PICKINESS = 4.0      # how sharply it prefers the side it values more
EXPLORE = 0.03       # it still tries the other side at least this often

# Betting: big when the chosen side's value (2 x win chance - 1) clears the bar, that is
# when it expects to win at least ~68% of the time. Fear does not make it hold back: in a
# death match that only gets you shot. Played by the rules alone, a player that picks the
# likelier side 90% of the time and bets like this beat the Rookie bot in 73% of games;
# one that bet big only when near certain, in 60%.
BIG_EDGE = 0.35
BET_SHARPNESS = 8.0

# Fear. Measured on the MaleCNS brain: at rest 4.5% of the fear circuit fires per 20 ms
# step; driven at full danger about 80% does (and the giant fibre fires most steps).
FEAR_REST = 0.045
FEAR_FULL = 0.80
THREAT_DRIVE = 0.8   # LC4 voltage per step at full danger
LOOM_DRIVE = 0.6     # LPLC2
PUNISH_DRIVE = 0.6   # PPL1
FEAR_SMOOTHING = 0.25
LOSS_AVERSION = 1.0  # full terror makes a loss count double

# Brain steps (20 ms each) per phase: (fast training, watching). The fly looks at the
# card for THINK steps (it averages steps THINK_FROM..THINK), then fear builds for FEAR
# steps before it bets. Those are the same in both modes, so both modes play the same
# fly; watching only adds suspense and time to see what happens. A new fly's brain first
# settles for a second ("wake"): its activity starts from nothing, and looks taken before
# it settles are unlike all the others. Flies get shot often, and without it the real
# brain picked the likelier side 64% of the time after 200 rounds, instead of 86%. After
# the last round the gun turns to the loser ("aim"), fires ("shot"), and a shot fly lies
# "dead"; a fly that lives hits the "jackpot".
PHASES = {"wake": (50, 50), "blank": (2, 12), "think": (20, 20), "fear": (6, 6), "suspense": (0, 45),
          "reveal": (4, 60), "aim": (8, 80), "shot": (2, 50), "dead": (2, 110), "jackpot": (2, 230), "end": (2, 110)}
THINK_FROM = 5

BOTS = {
    "random": "Random bot",   # flips coins
    "rookie": "Rookie bot",   # usually picks the likelier side, bets on a whim
    "pro": "Pro bot",         # always picks the likelier side, bets big only on near-certainties
}


def win_chance(card, higher):
    """Chance that a guess wins: the next card is strictly higher/lower (ties lose)."""
    return (RANKS - card) / RANKS if higher else (card - 1) / RANKS


def likelier_higher(card, rng=None):
    """The side more likely to win (a coin flip on a 7)."""
    if card == (RANKS + 1) // 2:
        return bool(rng.random() < 0.5) if rng is not None else True
    return card < (RANKS + 1) / 2


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))


def board_image(card=None):
    """What the fly sees: a dark board of 13 slots with the dealt card lit up."""
    img = np.full((BOARD_H, BOARD_W, 4), 16, dtype=np.uint8)
    img[:, :, 3] = 255
    slot = BOARD_W // RANKS
    for r in range(RANKS):
        cv2.rectangle(img, (r * slot + 2, 16), (r * slot + slot - 3, BOARD_H - 17), (40, 40, 46, 255), 1)
    if card:
        x0 = (card - 1) * slot
        cv2.rectangle(img, (x0 + 1, 12), (x0 + slot - 2, BOARD_H - 13), (245, 245, 245, 255), -1)
        cv2.putText(img, RANK_NAMES[card], (x0 + 2, 30), cv2.FONT_HERSHEY_PLAIN, 0.8, (20, 20, 20, 255), 1)
    return img


def barrel_image(t):
    """The gun turning on the fly, `t` from 0 to 1: a dark muzzle looming over the board."""
    img = board_image()
    centre = (BOARD_W // 2, BOARD_H // 2)
    r = int(6 + t * t * BOARD_W * 0.45)
    cv2.circle(img, centre, r + max(2, r // 5), (70, 70, 76, 255), -1)   # the barrel's rim
    cv2.circle(img, centre, r, (0, 0, 0, 255), -1)                        # and its bore
    return img


class Seat:
    """A player's chips and this round's bet."""

    def __init__(self, name):
        self.name = name
        self.chips = START_CHIPS
        self.shot = False
        self.new_round()

    def new_round(self):
        self.choice = None      # "higher" / "lower"
        self.bet = 0
        self.result = None      # "win" / "lose"

    @property
    def broke(self):
        return self.chips <= 0

    def place(self, higher, big, stake):
        """Bet on a side. Nobody can bet more chips than they have: at most, all in."""
        self.choice = "higher" if higher else "lower"
        self.bet = min(stake * (BIG_BET if big else 1), self.chips)

    def settle(self, card, nxt):
        """Pay out this round. Returns True if the bet won."""
        won = nxt > card if self.choice == "higher" else nxt < card
        self.result = "win" if won else "lose"
        self.chips += self.bet if won else -self.bet
        return won

    def as_dict(self):
        return {"name": self.name, "chips": self.chips, "choice": self.choice, "bet": self.bet,
                "result": self.result, "shot": self.shot}


class Bot:
    """The fly's opponent at the table."""

    def __init__(self, level="rookie", rng=None):
        if level not in BOTS:
            raise ValueError(f"unknown bot {level!r}; choose from {sorted(BOTS)}")
        self.level = level
        self.name = BOTS[level]
        self.rng = rng or np.random.default_rng()

    def decide(self, card):
        """(higher, big) for this card."""
        rng = self.rng
        if self.level == "random":
            return bool(rng.random() < 0.5), bool(rng.random() < 0.5)
        best = likelier_higher(card, rng)
        if self.level == "rookie":
            return (best if rng.random() < 0.75 else not best), bool(rng.random() < 0.3)
        return best, win_chance(card, best) >= 0.75


class Fear:
    """Danger in, terror out, through the fly's real fear circuit."""

    def __init__(self, components, strength=1.0):
        from fly_jjs.core.dashboard import circuit_members
        brain = components.brain
        self.strength = max(0.0, float(strength))
        self.circuit = circuit_members(brain)["fear"]
        self.mask = np.zeros(brain.n, dtype=bool)
        self.mask[self.circuit] = True
        groups = getattr(brain, "groups", {}) or {}
        self.escape = np.zeros(brain.n, dtype=bool)
        for key in ("escape_L", "escape_R"):
            if key in groups:
                self.escape[np.asarray(groups[key])] = True
        self.threat_cells = brain.cells(["LC4"])
        self.loom_cells = brain.cells(["LPLC2"])
        self.punish_cells = components.punish_dans
        self.reset()

    def reset(self):
        self.danger = 0.0
        self.rate = FEAR_REST
        self.escape_rate = 0.0
        self.terror = 0.0

    def assess(self, chips, rival, rnd, stake=1, dread=0.0, rounds=ROUNDS):
        """How much danger the fly is in (0..1). After the last round whoever has fewer
        chips is shot, so danger grows as the end nears (`urgency`) and with how far behind
        `rival` the fly is (`behind`, 0.5 when level), plus the `dread` chance it gives
        itself of losing this round (0.5 when it has no idea)."""
        urgency = min(1.0, rnd / rounds)
        behind = float(np.clip(0.5 + (rival - chips) / (2.0 * BIG_BET * stake), 0.0, 1.0))
        expected_loss = float(np.clip((dread - 0.2) / 0.8, 0.0, 1.0))
        danger = urgency * (0.2 + 0.6 * behind) + 0.4 * expected_loss
        self.danger = float(np.clip(danger * self.strength, 0.0, 1.0))
        return self.danger

    def injections(self):
        """Drive for the fear circuit at the current danger."""
        d = self.danger
        if d <= 0.0:
            return []
        return [(self.threat_cells, THREAT_DRIVE * d), (self.loom_cells, LOOM_DRIVE * d),
                (self.punish_cells, PUNISH_DRIVE * d)]

    def listen(self, fired):
        """After every brain step: how much of the fear circuit fired."""
        fired = np.asarray(fired)
        share = float(np.count_nonzero(self.mask[fired])) / max(len(self.circuit), 1)
        self.rate += FEAR_SMOOTHING * (share - self.rate)
        self.escape_rate += FEAR_SMOOTHING * (float(np.count_nonzero(self.escape[fired]) > 0) - self.escape_rate)
        self.terror = float(np.clip((self.rate - FEAR_REST) / (FEAR_FULL - FEAR_REST), 0.0, 1.0))

    def label(self):
        if self.escape_rate > 0.3:
            return "giant fibre (escape) firing"
        if self.terror > 0.55:
            return "fear circuit highly active"
        if self.danger > 0.3:
            return "danger sensed"
        return "calm"


class ChoiceValues:
    """What each choice ("higher", "lower") is worth for the card in view.

    One linear value per choice over the fly's card state, in units of 2 x win chance - 1.
    After a round the chosen value moves toward what happened by a step proportional to
    the surprise (delta = outcome - expected, the dopamine signal), normalised by the
    size of the card state, so learning is stable however many neurons are active.
    """

    def __init__(self, n_inputs, n_choices=2, lr=VALUE_LR):
        self.w = np.zeros((n_inputs, n_choices), dtype=np.float32)
        self.b = np.zeros(n_choices, dtype=np.float32)
        self.lr = lr

    def values(self, state):
        return state @ self.w + self.b

    def learn(self, state, choice, outcome):
        """Returns the prediction error (dopamine)."""
        delta = float(np.clip(outcome - self.values(state)[choice], -2.0, 2.0))
        self.w[:, choice] += np.float32(self.lr * delta / (float(state @ state) + 1.0)) * state
        self.b[choice] += np.float32(BIAS_LR * delta)
        return delta


class CasinoFly:
    """The fly at the table: eyes on the board, a fear circuit, and learned values."""

    def __init__(self, components, cfg, learn=True, seed=None, readout=None):
        from fly_jjs.core.brain import FlyBody
        from fly_jjs.core.vision import FlyEyes
        self.c = components
        self.learn = learn
        self.rng = np.random.default_rng(seed)
        self.eyes = FlyEyes(components.brain, cfg.get("resolution", "64x48"), cfg.get("use_color", True),
                            frame_aspect=BOARD_W / BOARD_H)
        if readout is None and cfg.get("readout", "full") == "descending":
            readout = components.dns
        self.body = FlyBody(components, self.eyes, steps=1, readout=readout)
        self.values = ChoiceValues(self.body.num_inputs)
        self.fear = Fear(components, cfg.get("fear", 1.0))
        self.body.listeners.append(self.fear.listen)
        self.usual = None           # its usual brain state after looking at a card
        self.looks = 0
        self.card_state = np.zeros(self.body.num_inputs, dtype=np.float32)
        self.by_card = {}           # its latest look at each card, for the strategy chart
        self._sum, self._count = None, 0
        self.choice = 0
        self.fresh = True           # its brain has not settled yet

    def step(self, img, dopamine=0.0, gather=False):
        x = self.body.step(img, (0, 0, 0), 0.0, dopamine, extra=self.fear.injections())
        if gather:
            self._sum = x.copy() if self._sum is None else self._sum + x
            self._count += 1
        return x

    def perceive(self, card):
        """Take in the dealt card: the brain state averaged over the look, relative to the
        fly's usual state. Most activity is the same whatever the card; what is left is
        what is special about this card (a linear probe tells low from high cards in it
        perfectly)."""
        look = self._sum / max(self._count, 1) if self._sum is not None else self.body.rates.copy()
        self._sum, self._count = None, 0
        self.looks += 1
        if self.usual is None:
            self.usual = look.copy()
        else:
            self.usual += max(USUAL_RATE, 1.0 / self.looks) * (look - self.usual)
        self.by_card[card] = look
        self.card_state = (look - self.usual).astype(np.float32)
        return self.card_state

    def odds(self, state=None):
        """(values, chance of saying "higher") for a card state (default: the dealt card)."""
        q = self.values.values(self.card_state if state is None else state)
        p_higher = float(np.clip(_sigmoid(PICKINESS * (q[0] - q[1])), EXPLORE, 1.0 - EXPLORE))
        return q, p_higher

    def dread(self):
        """How likely it thinks it is to lose on the dealt card (0.5: no idea yet)."""
        q, _ = self.odds()
        return float(np.clip((1.0 - np.clip(max(q[0], q[1]), -1.0, 1.0)) / 2.0, 0.0, 1.0))

    def decide(self):
        """(higher, big, (p_higher, p_big)) for the dealt card: big when it is confident."""
        q, p_higher = self.odds()
        higher = bool(self.rng.random() < p_higher)
        self.choice = 0 if higher else 1
        p_big = float(_sigmoid(BET_SHARPNESS * (q[self.choice] - BIG_EDGE)))
        big = bool(self.rng.random() < p_big)
        return higher, big, (p_higher, p_big)

    def outcome(self, won, terror_at_bet=0.0):
        """Learn from the round. Returns the dopamine (prediction error)."""
        target = 1.0 if won else -(1.0 + LOSS_AVERSION * terror_at_bet * self.fear.strength)
        if self.learn:
            return self.values.learn(self.card_state, self.choice, target)
        return float(np.clip(target - self.values.values(self.card_state)[self.choice], -2.0, 2.0))

    def strategy(self):
        """What it would do with each card it has seen: chance of "higher" and how sure
        it is of winning (the value of its preferred side as a win chance)."""
        out = []
        for card in range(1, RANKS + 1):
            if card not in self.by_card or self.usual is None:
                out.append(None)
                continue
            q, p_higher = self.odds((self.by_card[card] - self.usual).astype(np.float32))
            out.append({"p_higher": round(p_higher, 3), "win": round(float(np.clip((max(q) + 1) / 2, 0, 1)), 3)})
        return out

    def new_life(self, seed=None):
        """A new fly takes the seat: fresh brain activity, same learned values."""
        self.c.brain.reset(seed)
        self.body.trace.reset()
        self.body.pop_baseline = None
        self.eyes.reset()
        self.fear.reset()
        self._sum, self._count = None, 0
        self.fresh = True

    def save(self, path):
        np.savez(path, w=self.values.w, b=self.values.b, looks=self.looks,
                 usual=self.usual if self.usual is not None else np.zeros(0, np.float32))
        print(f"[Casino] Saved what the fly learned ({self.looks} cards seen) to {path}")

    def load(self, path):
        try:
            with np.load(path) as saved:
                if saved["w"].shape != self.values.w.shape:
                    print("[Casino] Saved casino memory is for a different readout; starting fresh.")
                    return False
                self.values.w, self.values.b = saved["w"], saved["b"]
                self.looks = int(saved["looks"])
                self.usual = saved["usual"] if saved["usual"].size else None
        except FileNotFoundError:
            print("[Casino] No casino memory yet: this fly has never gambled.")
            return False
        except Exception as e:
            print(f"[Casino] Could not read {path} ({e}); starting fresh.")
            return False
        print(f"[Casino] Loaded what earlier flies learned ({self.looks} cards seen).")
        return True


class StopCasino(Exception):
    pass


class Casino:
    """Runs death matches at Higher or Lower for the fly (and a bot), with an optional dashboard."""

    def __init__(self, components, cfg, bot="rookie", mode="show", learn=True, seed=None, readout=None,
                 dashboard=None, verbose=True):
        self.rng = np.random.default_rng(seed)
        self.fly = CasinoFly(components, cfg, learn=learn, seed=seed, readout=readout)
        self.bot = Bot(bot, np.random.default_rng(None if seed is None else seed + 1)) if bot else None
        self.mode = mode
        self.fast = mode != "show"
        self.dash = dashboard
        if dashboard is not None:
            dashboard.attach(self.fly.body)
        self.verbose = verbose
        self.generation = 1
        self.deaths = 0
        self.draws = 0
        self.duels = {"fly": 0, "bot": 0, "draw": 0}
        self.rounds = 0
        self.games = 0
        self.steps = 0
        self.recent = deque(maxlen=100)     # (won, smart) per fly decision
        self.history = deque(maxlen=10)     # this game's rounds, for the scoreboard
        self.log = deque(maxlen=6)
        self.banner = None
        self.table = {}
        self.probs = None

    # ---- brain time ---------------------------------------------------------------------

    def _run(self, phase, img, dopamine=0.0, dead=False):
        """Run the brain through a phase. `img` is what the fly sees, or a function of the
        phase's progress (0 to 1) for a moving picture. A dead fly's brain is not run: on
        the dashboard it falls silent."""
        steps = PHASES[phase][0 if self.fast else 1]
        dt = float(getattr(self.fly.c.brain, "dt", 0.02))
        silence = np.zeros(0, dtype=np.int64)
        for k in range(steps):
            tick = time.time()
            frame = img(k / max(steps - 1, 1)) if callable(img) else img
            if dead:
                if self.dash is not None:
                    self.dash.record(silence)
            else:
                self.fly.step(frame, dopamine, gather=phase == "think" and k + 1 >= THINK_FROM)
            self.steps += 1
            if self.dash is not None:
                if k == 0 or self.steps % 3 == 0:        # every phase is shown, however short
                    if callable(img):
                        self.dash.show_eye(frame)
                    self._publish()
                if "stop" in self.dash.take_pokes():
                    raise StopCasino
            if not self.fast:
                time.sleep(max(0.0, dt - (time.time() - tick)))

    def _show(self, img):
        if self.dash is not None:
            self.dash.show_eye(img)

    def _publish(self):
        if self.dash is None:
            return
        fear = self.fly.fear
        fly = dict(self.table.get("fly") or {})
        if self.probs is not None:
            fly.update(p_higher=round(self.probs[0], 3), p_big=round(self.probs[1], 3))
        self.dash.publish(
            mode="casino", pokes=[], log=list(self.log),
            title=f"Fly #{self.generation}" + (f" vs {self.bot.name}" if self.bot else " vs the house"),
            fear={"terror": round(fear.terror, 3), "danger": round(fear.danger, 3), "label": fear.label()},
            casino={**self.table, "fly": fly, "show": not self.fast, "stats": self.stats(), "banner": self.banner,
                    "history": list(self.history),
                    "strategy": self.fly.strategy() if self.steps % 30 == 0 or "strategy" not in self.table
                    else self.table["strategy"]})

    def stats(self):
        won = [w for w, _ in self.recent]
        smart = [s for _, s in self.recent]
        out = {"generation": self.generation, "games": self.games, "deaths": self.deaths,
               "survived": self.games - self.deaths, "draws": self.draws, "rounds": self.rounds,
               "smart_pct": round(100 * float(np.mean(smart)), 1) if smart else None,
               "winrate_pct": round(100 * float(np.mean(won)), 1) if won else None}
        if self.bot:
            out["duels"] = dict(self.duels)
        return out

    def _say(self, text):
        self.log.appendleft(text)
        if self.verbose and not self.fast:
            print(f"[Casino] {text}")

    def _deal(self):
        return int(self.rng.integers(1, RANKS + 1)), SUITS[self.rng.integers(4)]

    # ---- one game -----------------------------------------------------------------------

    def play_game(self, rounds=ROUNDS):
        """One death match. Returns the outcome: "survived" (the bot was shot, or the fly
        beat the house), "shot" (the fly was), "both shot" or "draw"."""
        fly = Seat(f"Fly #{self.generation}")
        bot = Seat(self.bot.name) if self.bot else None
        seats = [fly] + ([bot] if bot else [])
        card, suit = self._deal()
        self.banner = None
        self.history.clear()
        if self.fly.fresh:
            self.table.update({"game": self.games + 1, "round": 1, "rounds": rounds, "stake": 1, "phase": "wake",
                               "target": None, "start_chips": START_CHIPS, "big_bet": BIG_BET,
                               "card": None, "card_suit": None, "next": None, "next_suit": None,
                               "fly": fly.as_dict(), "bot": bot.as_dict() if bot else None})
            self.fly.fear.danger = 0.0
            self._run("wake", board_image())
            self.fly.fresh = False
        rnd = 0
        while True:
            rnd += 1
            final = rnd >= rounds
            stake = FINAL_STAKE if final else 1
            for seat in seats:
                seat.new_round()
            self.probs = None
            self.table.update({"game": self.games + 1, "round": rnd, "rounds": rounds, "stake": stake,
                               "phase": "think", "target": None, "start_chips": START_CHIPS, "big_bet": BIG_BET,
                               "card": card, "card_suit": suit, "next": None, "next_suit": None,
                               "fly": fly.as_dict(), "bot": bot.as_dict() if bot else None})
            rival = bot.chips if bot else START_CHIPS
            self.fly.fear.assess(fly.chips, rival, rnd, stake, rounds=rounds)
            self._run("blank", board_image())
            seen = board_image(card)
            self._show(seen)
            self._run("think", seen)
            self.fly.perceive(card)
            # Its expectation of this card sets in, and a bad card is frightening.
            self.fly.fear.assess(fly.chips, rival, rnd, stake, dread=self.fly.dread(), rounds=rounds)
            self._run("fear", seen)

            higher, big, self.probs = self.fly.decide()
            terror_at_bet = self.fly.fear.terror
            fly.place(higher, big, stake)
            if bot:
                bot.place(*self.bot.decide(card), stake)
            self.table.update(phase="wait", fly=fly.as_dict(), bot=bot.as_dict() if bot else None)
            self._run("suspense", seen)

            nxt, nsuit = self._deal()
            won = fly.settle(card, nxt)
            self.recent.append((won, card == (RANKS + 1) // 2 or higher == likelier_higher(card)))
            if bot:
                bot.settle(card, nxt)
            self.rounds += 1
            dopamine = self.fly.outcome(won, terror_at_bet)
            self.history.append({"round": rnd, "card": card, "next": nxt,
                                 "fly": {"choice": fly.choice, "bet": fly.bet, "won": won},
                                 "bot": {"choice": bot.choice, "bet": bot.bet, "won": bot.result == "win"}
                                 if bot else None})

            self._say(f"{fly.name}: {RANK_NAMES[card]}, {fly.choice} for {fly.bet}. {RANK_NAMES[nxt]} came, "
                      f"{'won' if won else 'lost'}. {fly.chips} chips.")
            self.table.update(phase="reveal", next=nxt, next_suit=nsuit, fly=fly.as_dict(),
                              bot=bot.as_dict() if bot else None)
            rival = bot.chips if bot else START_CHIPS
            self.fly.fear.assess(fly.chips, rival, rnd, stake, rounds=rounds)
            reveal = board_image(nxt)
            self._show(reveal)
            self._run("reveal", reveal, dopamine=dopamine)
            card, suit = nxt, nsuit
            if any(seat.broke for seat in seats) or (final and fly.chips != rival) or rnd >= rounds + SUDDEN_DEATH:
                break

        rival = bot.chips if bot else START_CHIPS
        if fly.broke and bot is not None and bot.broke:
            outcome = "both shot"
        elif fly.broke or fly.chips < rival:
            outcome = "shot"
        elif (bot is not None and bot.broke) or fly.chips > rival:
            outcome = "survived"
        else:
            outcome = "draw"
        self._finish(outcome, fly, bot)
        return outcome

    def _why(self, seat, fly, bot):
        """Why a player is being shot."""
        if seat.broke:
            return f"{seat.name} ran out of chips"
        if bot is None:
            return f"{seat.name} ended with {seat.chips} chips, fewer than the {START_CHIPS} it started with"
        other = bot if seat is fly else fly
        return f"{seat.name} was behind, {seat.chips} to {other.chips}"

    def _finish(self, outcome, fly, bot):
        self.games += 1
        if bot:
            self.duels[{"survived": "fly", "shot": "bot"}.get(outcome, "draw")] += 1
        seats = {"fly": fly, "bot": bot}
        targets = {"shot": ["fly"], "both shot": ["fly", "bot"], "survived": ["bot"] if bot else []}.get(outcome, [])
        empty = board_image()
        next_fly = f"Fly #{self.generation + 1} takes the seat and keeps what was learned."
        if targets:
            why = " and ".join(self._why(seats[t], fly, bot) for t in targets)
            self._say(f"{why}. The gun turns to {'them' if len(targets) > 1 else 'it'}.")
            self.table.update(phase="aim", target=targets)
            if "fly" in targets:
                # It sees the barrel coming at it, and its fear circuit fires as hard as it can.
                fear = self.fly.fear
                fear.danger = max(fear.strength, 0.5) if fear.strength else 0.0
                self._run("aim", barrel_image, dopamine=-0.5)
            else:
                self._run("aim", empty)
            for t in targets:
                seats[t].shot = True
            self.table.update(phase="shot", fly=fly.as_dict(), bot=bot.as_dict() if bot else None)
            if "fly" in targets:
                self.deaths += 1
                self._run("shot", empty, dead=True)
                self.banner = {"kind": "dead", "title": "Both shot" if len(targets) > 1 else "Shot",
                               "detail": f"{why}. {next_fly}"}
                self._say(f"{fly.name} was shot. {next_fly}")
                self.table.update(phase="dead")
                self._run("dead", empty, dead=True)
                self.generation += 1
                self.fly.new_life(int(self.rng.integers(1 << 30)))
            else:
                self.fly.fear.danger = 0.0
                self._run("shot", empty, dopamine=1.0)     # relief: the gun went off, and not at the fly
        if outcome == "survived":
            detail = (f"{self._why(bot, fly, bot)}{'' if bot.broke else ','} and got shot. {fly.name} lives." if bot else
                      f"{fly.name} beat the house, {fly.chips} chips from {START_CHIPS}, and walks free.")
            self.banner = {"kind": "jackpot", "title": "Jackpot", "detail": detail}
            self._say(detail)
            self.fly.fear.danger = 0.0
            self.table.update(phase="jackpot")
            self._run("jackpot", empty, dopamine=0.5)
        elif outcome == "draw":
            self.draws += 1
            rival = bot.chips if bot else START_CHIPS
            self.banner = {"kind": "neutral", "title": "Draw",
                           "detail": f"Still level, {fly.chips} to {rival}, after sudden death. The gun stays down."}
            self._say(self.banner["detail"])
            self.fly.fear.danger = 0.0
            self.table.update(phase="end")
            self._run("end", empty)
        if self.verbose:
            s = self.stats()
            print(f"[Casino] Game {self.games}: {outcome.upper():9s} | {self.table['round']} rounds | "
                  f"chips {fly.chips}" + (f" vs {bot.chips}" if bot else "")
                  + f" | smart picks {s['smart_pct']}% | flies shot {self.deaths}"
                  + (f" | games fly {self.duels['fly']}-{self.duels['bot']} bot" if self.bot else ""))
        self.banner = None


def casino_memory_path():
    from fly_jjs.core.storage import USER_DIR
    return os.path.join(USER_DIR, "casino", "casino_memory.npz")


def run_casino(games=None, mode="show", bot="rookie", fear=None, learn=True, seed=None, readout=None,
               dashboard=True, open_browser=True, memory_path=None, verbose=True):
    """Let the fly play death matches. `mode` "show" plays in real time for watching;
    "fast" trains. Runs `games` games (None: until stopped). Returns the Casino with its
    statistics."""
    from fly_jjs.core.brain import get_brain_components
    from fly_jjs.core.config import ConfigManager
    from fly_jjs.core.dashboard import DEFAULT_PORT, BrainDashboard

    cfg = dict(ConfigManager.load_config())
    if fear is not None:
        cfg["fear"] = fear
    components = get_brain_components()
    dash = None
    if dashboard:
        dash = BrainDashboard(components.brain, port=cfg.get("dashboard_port", DEFAULT_PORT))
        dash.start(open_browser=open_browser)
    casino = Casino(components, cfg, bot=bot, mode=mode, learn=learn, seed=seed, readout=readout,
                    dashboard=dash, verbose=verbose)
    path = memory_path or casino_memory_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    casino.fly.load(path)
    print("[Casino] Fly #1 sits down" + (f" against the {casino.bot.name}" if casino.bot else " against the house")
          + f". {ROUNDS} rounds a game; whoever is behind at the end gets shot. Fear strength "
          f"{casino.fly.fear.strength:g}. Stop with Ctrl+C" + (" or Stop on the page." if dash else "."))
    try:
        while games is None or casino.games < games:
            casino.play_game()
            if learn and casino.games % 10 == 0:
                casino.fly.save(path)
    except (KeyboardInterrupt, StopCasino):
        print("\n[Casino] Stopped.")
    finally:
        if learn:
            casino.fly.save(path)
        if dash is not None:
            dash.stop()
    return casino
