"""The casino: the fly gambles with its money and its life.

Three games, one fly, one wallet. Every fly sits down with $1,000; broke means shot.

* Death match (cards): Higher or Lower against a bot. A card is dealt; each player says
  whether the next card will be higher or lower and bets chips on it (ties lose). Win
  and you gain what you bet, lose and you lose it. A game is three rounds, the last for
  double stakes. Then whoever has fewer chips is shot; if they are level, sudden-death
  rounds decide it. Run out of chips and you are shot on the spot. Alone at the table
  the fly plays the house: it is shot if it ends the game with fewer chips than it
  started with. Chips are bought for $10 each and cashed out at the end.
* Slots (slots.py) and the horse races (race.py).

How the fly plays
-----------------
* It sees the table with its own eyes: the dealt card lights up on a board of 13
  slots, ace on the far left and king on the far right, the way flies are shown bars
  in lab arenas. It looks for 0.4 s; its readout neurons (about 59,000), averaged over
  that look and taken relative to its usual state, are what it knows about the card.
* It learns what each choice is worth for what is in view: for the cards one value for
  "higher" and one for "lower". After every round the chosen value moves toward what
  happened, in proportion to the surprise (delta = outcome - expected): the dopamine
  signal. It is sent back into the brain as reward (PAM neurons) or punishment (PPL1)
  dopamine. Each game has its own values (a `Mind`); the brain is the same.
* It picks the side it values more (mostly), and bets big when it is confident the
  side will win.
* It is afraid. Danger (at the cards: how near the end of the game is, how far behind it
  is, and how likely it thinks it is to lose on this card) drives its real fear circuit:
  the LC4 and LPLC2 threat and looming detectors and the PPL1 punishment neurons. The
  connectome carries that on to the giant fibre (DNp01), the neuron that fires the
  escape jump. The terror meter is how hard that circuit fires: measured, not made up.
  The more terrified it was when it bet, the more a loss teaches it. (At the cards
  terror does not make it bet small: in a death match holding back only gets you shot.)
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

from fly_jjs.core.wallet import Wallet

RANKS = 13
RANK_NAMES = ("", "A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
SUITS = "SHDC"
START_CHIPS = 10
CHIP_VALUE = 10      # dollars a chip
BIG_BET = 3          # a big bet risks three times the stake
ROUNDS = 3           # rounds in a game; then whoever is behind is shot
FINAL_STAKE = 2      # the last round, and sudden death, are for double stakes
SUDDEN_DEATH = 5     # still level after this many extra rounds: a draw, nobody is shot

# The fly's eye view of every game: 208 x 104. At the cards, 13 slots, ace on the far
# left and king on the far right.
BOARD_W, BOARD_H = 208, 104

# Learning. Replaying recorded brain states offline: learning on the raw state got
# nowhere (most activity is the same for every card), and an actor-critic sometimes
# locked into the wrong side for good; values per choice with normalised steps reached
# 86-94% smart picks within ~200 rounds on every seed tried.
VALUE_LR = 0.3       # normalised LMS step (stable for anything below 2)
BIAS_LR = 0.05
USUAL_RATE = 0.02    # the fly's usual brain state is followed over ~50 rounds
PICKINESS = 4.0      # how sharply it prefers the choice it values more
EXPLORE = 0.03       # it still tries each other choice at least this often

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
# brain picked the likelier side 64% of the time after 200 rounds, instead of 86%. The
# gun turns to the loser ("aim"), fires ("shot"), and a shot fly lies "dead"; a fly that
# lives hits the "jackpot" (timed to the jackpot sound: 4.8 s). Between games, when the
# casino is not looping, the brain idles half a second at a time until the viewer picks.
PHASES = {"wake": (50, 50), "blank": (2, 12), "think": (20, 20), "fear": (6, 6), "suspense": (0, 45),
          "reveal": (4, 60), "aim": (8, 80), "shot": (2, 50), "dead": (2, 110), "jackpot": (2, 260),
          "end": (2, 110), "idle": (1, 25)}
THINK_FROM = 5

BOTS = {
    "random": "Random bot",   # flips coins
    "rookie": "Rookie bot",   # usually picks the likelier side, bets on a whim
    "pro": "Pro bot",         # always picks the likelier side, bets big only on near-certainties
}
GAMES = {"cards": "Death match", "slots": "Slots", "race": "Horse races"}


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


def utility(net):
    """How a result feels, in stakes won (+) or lost (-), on a log scale: losing the stake
    is -0.69, doubling it +0.69, fifty times it +3.9. Big wins count for less than their
    size, so one jackpot does not swamp everything else the fly has learned."""
    return float(np.sign(net) * np.log1p(abs(net)))


def blank_image():
    img = np.full((BOARD_H, BOARD_W, 4), 16, dtype=np.uint8)
    img[:, :, 3] = 255
    return img


def board_image(card=None):
    """What the fly sees: a dark board of 13 slots with the dealt card lit up."""
    img = blank_image()
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

    def __init__(self, name, chips=START_CHIPS):
        self.name = name
        self.chips = chips
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

    def feel(self, danger):
        """Set the danger (0..1, before the fly's fear strength)."""
        self.danger = float(np.clip(danger * self.strength, 0.0, 1.0))
        return self.danger

    def assess(self, chips, rival, rnd, stake=1, dread=0.0, rounds=ROUNDS):
        """Danger at the cards. After the last round whoever has fewer chips is shot, so
        danger grows as the end nears (`urgency`) and with how far behind `rival` the fly
        is (`behind`, 0.5 when level), plus the `dread` chance it gives itself of losing
        this round (0.5 when it has no idea)."""
        urgency = min(1.0, rnd / rounds)
        behind = float(np.clip(0.5 + (rival - chips) / (2.0 * BIG_BET * stake), 0.0, 1.0))
        expected_loss = float(np.clip((dread - 0.2) / 0.8, 0.0, 1.0))
        return self.feel(urgency * (0.2 + 0.6 * behind) + 0.4 * expected_loss)

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
    """What each choice is worth for what is in view.

    One linear value per choice over the fly's state. After a round the chosen value
    moves toward what happened by a step proportional to the surprise (delta = outcome -
    expected, the dopamine signal), normalised by the size of the state, so learning is
    stable however many neurons are active.
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


class Mind:
    """What the fly has learned about one game: a value for each choice over its brain
    state, taken relative to its usual state when looking at that game."""

    def __init__(self, n_inputs, choices):
        self.choices = tuple(choices)
        self.values = ChoiceValues(n_inputs, len(self.choices))
        self.usual = None
        self.looks = 0
        self.state = np.zeros(n_inputs, dtype=np.float32)

    def perceive(self, look):
        """Most activity is the same whatever is in view; what is left once the usual
        state is taken away is what is special about this view."""
        self.looks += 1
        if self.usual is None:
            self.usual = look.copy()
        else:
            self.usual += max(USUAL_RATE, 1.0 / self.looks) * (look - self.usual)
        self.state = (look - self.usual).astype(np.float32)
        return self.state

    def relative(self, look):
        if self.usual is None:
            return np.zeros_like(self.state)
        return (look - self.usual).astype(np.float32)

    def probs(self, state=None, bias=None):
        """(values, chance of each choice): a softmax over the values (plus `bias`), with
        every choice kept at EXPLORE or more."""
        q = self.values.values(self.state if state is None else state)
        z = PICKINESS * (q + (0.0 if bias is None else np.asarray(bias, dtype=np.float32)))
        p = np.exp(z - z.max())
        p = np.clip(p / p.sum(), EXPLORE, 1.0)
        return q, p / p.sum()

    def learn(self, choice, target, learn=True):
        """Move the chosen value toward `target`; returns the dopamine."""
        if learn:
            return self.values.learn(self.state, choice, target)
        return float(np.clip(target - self.values.values(self.state)[choice], -2.0, 2.0))

    def save_into(self, out, name):
        out[f"{name}_w"], out[f"{name}_b"] = self.values.w, self.values.b
        out[f"{name}_looks"] = self.looks
        out[f"{name}_usual"] = self.usual if self.usual is not None else np.zeros(0, np.float32)

    def load_from(self, saved, name):
        if f"{name}_w" not in saved.files:
            return False
        if saved[f"{name}_w"].shape != self.values.w.shape:
            print(f"[Casino] Saved {name} memory is for a different readout; starting that game fresh.")
            return False
        self.values.w, self.values.b = saved[f"{name}_w"], saved[f"{name}_b"]
        self.looks = int(saved[f"{name}_looks"])
        self.usual = saved[f"{name}_usual"] if saved[f"{name}_usual"].size else None
        return True


class CasinoFly:
    """The fly at the table: eyes, a fear circuit, and what it has learned about each game."""

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
        self.fear = Fear(components, cfg.get("fear", 1.0))
        self.body.listeners.append(self.fear.listen)
        self.minds = {"cards": Mind(self.body.num_inputs, ("higher", "lower"))}
        self.by_card = {}           # its latest look at each card, for the strategy chart
        self._sum, self._count = None, 0
        self.choice = 0
        self.fresh = True           # its brain has not settled yet

    def mind(self, game, choices):
        if game not in self.minds:
            self.minds[game] = Mind(self.body.num_inputs, choices)
        return self.minds[game]

    # The cards' mind, under the names the rest of the code (and saved files) grew up with.
    @property
    def values(self):
        return self.minds["cards"].values

    @property
    def usual(self):
        return self.minds["cards"].usual

    @usual.setter
    def usual(self, value):
        self.minds["cards"].usual = value

    @property
    def card_state(self):
        return self.minds["cards"].state

    @card_state.setter
    def card_state(self, value):
        self.minds["cards"].state = value

    @property
    def looks(self):
        return self.minds["cards"].looks

    def step(self, img, dopamine=0.0, gather=False):
        x = self.body.step(img, (0, 0, 0), 0.0, dopamine, extra=self.fear.injections())
        if gather:
            self._sum = x.copy() if self._sum is None else self._sum + x
            self._count += 1
        return x

    def look(self):
        """The brain state averaged over the last look (the gathered steps)."""
        look = self._sum / max(self._count, 1) if self._sum is not None else self.body.rates.copy()
        self._sum, self._count = None, 0
        return look

    # ---- the cards ----------------------------------------------------------------------

    def perceive(self, card):
        """Take in the dealt card: the brain state averaged over the look, relative to the
        fly's usual state. What is left is what is special about this card (a linear probe
        tells low from high cards in it perfectly)."""
        look = self.look()
        self.by_card[card] = look
        return self.minds["cards"].perceive(look)

    def odds(self, state=None):
        """(values, chance of saying "higher") for a card state (default: the dealt card)."""
        q, p = self.minds["cards"].probs(state)
        return q, float(p[0])

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
        return self.minds["cards"].learn(self.choice, target, learn=self.learn)

    def strategy(self):
        """What it would do with each card it has seen: chance of "higher" and how sure
        it is of winning (the value of its preferred side as a win chance)."""
        mind = self.minds["cards"]
        out = []
        for card in range(1, RANKS + 1):
            if card not in self.by_card or mind.usual is None:
                out.append(None)
                continue
            q, p_higher = self.odds(mind.relative(self.by_card[card]))
            out.append({"p_higher": round(p_higher, 3), "win": round(float(np.clip((max(q) + 1) / 2, 0, 1)), 3)})
        return out

    # ---- a new fly, and memory ------------------------------------------------------------

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
        out = {}
        for name, mind in self.minds.items():
            mind.save_into(out, name)
        np.savez(path, **out)
        seen = ", ".join(f"{name} {mind.looks}" for name, mind in self.minds.items())
        print(f"[Casino] Saved what the fly learned (looks: {seen}) to {path}")

    def load(self, path):
        try:
            with np.load(path) as saved:
                if "w" in saved.files:          # before the other games existed: the cards only
                    if saved["w"].shape != self.values.w.shape:
                        print("[Casino] Saved casino memory is for a different readout; starting fresh.")
                        return False
                    mind = self.minds["cards"]
                    mind.values.w, mind.values.b = saved["w"], saved["b"]
                    mind.looks = int(saved["looks"])
                    mind.usual = saved["usual"] if saved["usual"].size else None
                else:
                    from fly_jjs.core.race import RaceTable
                    from fly_jjs.core.slots import SlotTable
                    for name, choices in (("cards", ("higher", "lower")), ("slots", SlotTable.CHOICES),
                                          ("race", RaceTable.CHOICES)):
                        if f"{name}_w" in saved.files:
                            self.mind(name, choices).load_from(saved, name)
        except FileNotFoundError:
            print("[Casino] No casino memory yet: this fly has never gambled.")
            return False
        except Exception as e:
            print(f"[Casino] Could not read {path} ({e}); starting fresh.")
            return False
        seen = ", ".join(f"{name} {mind.looks}" for name, mind in self.minds.items())
        print(f"[Casino] Loaded what earlier flies learned (looks: {seen}).")
        return True


class StopCasino(Exception):
    pass


class Table:
    """What every game shares: the fly (its brain, eyes, fear and what it has learned), its
    wallet, the dashboard, brain time, the gun and the jackpot."""

    game = None
    phases = PHASES

    def __init__(self, components, cfg, mode="show", learn=True, seed=None, readout=None, dashboard=None,
                 verbose=True, fly=None, wallet=None, session=None):
        self.rng = np.random.default_rng(seed)
        self.fly = fly if fly is not None else CasinoFly(components, cfg, learn=learn, seed=seed, readout=readout)
        self.wallet = wallet if wallet is not None else Wallet()
        self.session = session if session is not None else {}
        self.mode = mode
        self.fast = mode != "show"
        self.dash = dashboard
        if dashboard is not None:
            dashboard.attach(self.fly.body)
        self.verbose = verbose
        self.games = 0
        self.steps = 0
        self.log = deque(maxlen=6)
        self.banner = None
        self.table = {}

    @property
    def generation(self):
        return self.wallet.generation

    @property
    def deaths(self):
        return self.wallet.deaths

    # ---- brain time ---------------------------------------------------------------------

    def _run(self, phase, img, dopamine=0.0, dead=False, steps=None):
        """Run the brain through a phase. `img` is what the fly sees, or a function of the
        phase's progress (0 to 1) for a moving picture. A dead fly's brain is not run: on
        the dashboard it falls silent."""
        if steps is None:
            steps = self.phases[phase][0 if self.fast else 1]
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
                self._pokes()
            if not self.fast:
                time.sleep(max(0.0, dt - (time.time() - tick)))

    def _pokes(self):
        """Buttons on the page: Stop, Loop, Play again, or another game (after this one)."""
        for poke in self.dash.take_pokes():
            if poke == "stop":
                raise StopCasino
            if poke == "loop":
                self.session["loop"] = not self.session.get("loop", False)
            elif poke == "again" or poke in GAMES:
                self.session["next"] = poke

    def _show(self, img):
        if self.dash is not None:
            self.dash.show_eye(img)

    def _publish(self):
        if self.dash is None:
            return
        fear = self.fly.fear
        session = {"loop": bool(self.session.get("loop")), "waiting": bool(self.session.get("waiting")),
                   "next": self.session.get("next"), "games": GAMES}
        self.dash.publish(
            mode="casino", pokes=[], log=list(self.log), title=self.title(),
            fear={"terror": round(fear.terror, 3), "danger": round(fear.danger, 3), "label": fear.label()},
            casino={**self.table, "game": self.game, "show": not self.fast, "stats": self.stats(),
                    "banner": self.banner, "wallet": self.wallet.as_dict(), "session": session, **self.extra()})

    def title(self):
        return f"Fly #{self.generation}"

    def extra(self):
        return {}

    def stats(self):
        return {"generation": self.generation, "games": self.games, "deaths": self.deaths}

    def _say(self, text):
        self.log.appendleft(text)
        if self.verbose and not self.fast:
            print(f"[Casino] {text}")

    # ---- shared moments -----------------------------------------------------------------

    def _wake(self, **table):
        """A new fly's brain settles for a second before its first look."""
        if not self.fly.fresh:
            return
        self.table.update(table)
        self.table.update(phase="wake", target=None)
        self.fly.fear.danger = 0.0
        self._run("wake", blank_image())
        self.fly.fresh = False

    def _execute(self, targets, why, mark=None):
        """The gun turns to `targets` ("fly", "bot") and fires. The doomed fly sees the
        barrel coming and its fear circuit fires as hard as it can; once shot its brain is
        no longer run, the house keeps its money and the next fly takes the seat.
        `mark(target)` marks a target shot in the table. Returns True if the fly died."""
        mark = mark or (lambda t: self.table.get(t) is not None and self.table[t].update(shot=True))
        self._say(f"{why}. The gun turns to {'them' if len(targets) > 1 else 'it'}.")
        self.table.update(phase="aim", target=list(targets))
        if "fly" in targets:
            fear = self.fly.fear
            fear.danger = max(fear.strength, 0.5) if fear.strength else 0.0
            self._run("aim", barrel_image, dopamine=-0.5)
        else:
            self._run("aim", board_image())
        for t in targets:
            mark(t)
        self.table.update(phase="shot")
        if "fly" not in targets:
            self.fly.fear.danger = 0.0
            self._run("shot", board_image(), dopamine=1.0)     # relief: the gun went off, and not at the fly
            return False
        name = f"Fly #{self.generation}"
        self._run("shot", blank_image(), dead=True)
        self.banner = {"kind": "dead", "title": "Both shot" if len(targets) > 1 else "Shot",
                       "detail": f"{why}. Fly #{self.generation + 1} takes the seat and keeps what was learned."}
        self._say(f"{name} was shot. Fly #{self.generation + 1} takes the seat.")
        self.table.update(phase="dead")
        self._run("dead", blank_image(), dead=True)
        self.wallet.died()
        self.fly.new_life(int(self.rng.integers(1 << 30)))
        return True

    def _jackpot(self, detail, dopamine=0.5):
        self.banner = {"kind": "jackpot", "title": "Jackpot", "detail": detail}
        self._say(detail)
        self.fly.fear.danger = 0.0
        self.table.update(phase="jackpot")
        self._run("jackpot", blank_image(), dopamine=dopamine)

    def wait(self):
        """Between games, when not looping: the brain idles until the viewer picks what is
        next on the page. Returns "again" or a game's name."""
        self.session["waiting"] = True
        self.banner = None
        try:
            while True:
                nxt = self.session.pop("next", None)
                if nxt:
                    return nxt
                if self.session.get("loop"):
                    return "again"
                self.fly.fear.danger = 0.0
                self._run("idle", blank_image())
        finally:
            self.session["waiting"] = False


class Casino(Table):
    """The death match at Higher or Lower, for the fly (and a bot)."""

    game = "cards"

    def __init__(self, components, cfg, bot="rookie", mode="show", learn=True, seed=None, readout=None,
                 dashboard=None, verbose=True, fly=None, wallet=None, session=None):
        super().__init__(components, cfg, mode=mode, learn=learn, seed=seed, readout=readout, dashboard=dashboard,
                         verbose=verbose, fly=fly, wallet=wallet, session=session)
        self.bot = Bot(bot, np.random.default_rng(None if seed is None else seed + 1)) if bot else None
        self.draws = 0
        self.shot_here = 0
        self.duels = {"fly": 0, "bot": 0, "draw": 0}
        self.rounds = 0
        self.recent = deque(maxlen=100)     # (won, smart) per fly decision
        self.history = deque(maxlen=10)     # this game's rounds, for the scoreboard
        self.probs = None

    def title(self):
        return f"Fly #{self.generation}" + (f" vs {self.bot.name}" if self.bot else " vs the house")

    def extra(self):
        fly = dict(self.table.get("fly") or {})
        if self.probs is not None:
            fly.update(p_higher=round(self.probs[0], 3), p_big=round(self.probs[1], 3))
        return {"fly": fly, "history": list(self.history), "bot_level": self.bot.level if self.bot else None,
                "chip_value": CHIP_VALUE}

    def _publish(self):
        if self.dash is not None and (self.steps % 30 == 0 or "strategy" not in self.table):
            self.table["strategy"] = self.fly.strategy()
        super()._publish()

    def stats(self):
        won = [w for w, _ in self.recent]
        smart = [s for _, s in self.recent]
        out = {"generation": self.generation, "games": self.games, "deaths": self.deaths,
               "survived": self.games - self.shot_here, "draws": self.draws, "rounds": self.rounds,
               "smart_pct": round(100 * float(np.mean(smart)), 1) if smart else None,
               "winrate_pct": round(100 * float(np.mean(won)), 1) if won else None}
        if self.bot:
            out["duels"] = dict(self.duels)
        return out

    # ---- one game -----------------------------------------------------------------------

    def play_game(self, rounds=ROUNDS):
        """One death match. Returns the outcome: "survived" (the bot was shot, or the fly
        beat the house), "shot" (the fly was), "both shot" or "draw"."""
        card, suit = self._deal()
        self.banner = None
        self.history.clear()
        buy_in = min(START_CHIPS, self.wallet.money // CHIP_VALUE)
        fly = Seat(f"Fly #{self.generation}", chips=buy_in)
        bot = Seat(self.bot.name) if self.bot else None
        seats = [fly] + ([bot] if bot else [])
        start = {"number": self.games + 1, "round": 1, "rounds": rounds, "stake": 1, "start_chips": START_CHIPS,
                 "big_bet": BIG_BET, "card": None, "card_suit": None, "next": None, "next_suit": None,
                 "fly": fly.as_dict(), "bot": bot.as_dict() if bot else None}
        self._wake(**start)
        if buy_in == 0:
            self.table.update(start)
            return self._finish("shot", fly, bot, broke=True)
        self.wallet.change(-buy_in * CHIP_VALUE, f"Death match: bought {buy_in} chips")
        rnd = 0
        while True:
            rnd += 1
            final = rnd >= rounds
            stake = FINAL_STAKE if final else 1
            for seat in seats:
                seat.new_round()
            self.probs = None
            self.table.update({**start, "round": rnd, "stake": stake, "phase": "think", "target": None,
                               "card": card, "card_suit": suit, "fly": fly.as_dict(), "bot": bot.as_dict() if bot else None})
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
        return self._finish(outcome, fly, bot)

    def _deal(self):
        return int(self.rng.integers(1, RANKS + 1)), SUITS[self.rng.integers(4)]

    def _why(self, seat, fly, bot):
        """Why a player is being shot."""
        if seat.broke:
            return f"{seat.name} ran out of chips"
        if bot is None:
            return f"{seat.name} ended with {seat.chips} chips, fewer than the {START_CHIPS} it started with"
        other = bot if seat is fly else fly
        return f"{seat.name} was behind, {seat.chips} to {other.chips}"

    def _finish(self, outcome, fly, bot, broke=False):
        self.games += 1
        if bot:
            self.duels[{"survived": "fly", "shot": "bot"}.get(outcome, "draw")] += 1
        seats = {"fly": fly, "bot": bot}
        targets = {"shot": ["fly"], "both shot": ["fly", "bot"], "survived": ["bot"] if bot else []}.get(outcome, [])

        def mark(t):
            seats[t].shot = True
            self.table[t] = seats[t].as_dict()

        if targets:
            why = (f"{fly.name} is broke: ${self.wallet.money} left, not enough for a chip" if broke else
                   " and ".join(self._why(seats[t], fly, bot) for t in targets))
            if self._execute(targets, why, mark):
                self.shot_here += 1
        if outcome in ("survived", "draw"):
            cash = self.wallet.change(fly.chips * CHIP_VALUE, f"Death match: cashed out {fly.chips} chips")
            self._say(f"{fly.name} cashes out ${cash}.")
        if outcome == "survived":
            detail = (f"{self._why(bot, fly, bot)}{'' if bot.broke else ','} and got shot. {fly.name} lives."
                      if bot else f"{fly.name} beat the house, {fly.chips} chips from {START_CHIPS}, and walks free.")
            self._jackpot(detail)
        elif outcome == "draw":
            self.draws += 1
            rival = bot.chips if bot else START_CHIPS
            self.banner = {"kind": "neutral", "title": "Draw",
                           "detail": f"Still level, {fly.chips} to {rival}, after sudden death. The gun stays down."}
            self._say(self.banner["detail"])
            self.fly.fear.danger = 0.0
            self.table.update(phase="end")
            self._run("end", board_image())
        self.wallet.end_game()
        if self.verbose:
            s = self.stats()
            print(f"[Casino] Game {self.games}: {outcome.upper():9s} | {self.table['round']} rounds | "
                  f"chips {fly.chips}" + (f" vs {bot.chips}" if bot else "")
                  + f" | ${self.wallet.money} | smart picks {s['smart_pct']}% | flies shot {self.deaths}"
                  + (f" | games fly {self.duels['fly']}-{self.duels['bot']} bot" if self.bot else ""))
        return outcome


# ---- running the casino -------------------------------------------------------------------

def casino_memory_path():
    from fly_jjs.core.storage import USER_DIR
    return os.path.join(USER_DIR, "casino", "casino_memory.npz")


def wallet_path():
    from fly_jjs.core.storage import USER_DIR
    return os.path.join(USER_DIR, "casino", "wallet.json")


def make_table(game, components, cfg, fly, wallet, session, mode="show", bot="rookie", seed=None, dashboard=None,
               verbose=True):
    from fly_jjs.core.race import RaceTable
    from fly_jjs.core.slots import SlotTable
    common = dict(mode=mode, seed=seed, dashboard=dashboard, verbose=verbose, fly=fly, wallet=wallet, session=session)
    if game == "slots":
        return SlotTable(components, cfg, **common)
    if game == "race":
        return RaceTable(components, cfg, **common)
    return Casino(components, cfg, bot=bot, **common)


def run_casino(game="cards", games=None, mode="show", bot="rookie", fear=None, learn=True, seed=None, readout=None,
               dashboard=True, open_browser=True, memory_path=None, money_path=None, loop=None, verbose=True):
    """Let the fly gamble. `game`: "cards" (the death match), "slots" or "race". `mode`
    "show" plays in real time for watching; "fast" trains. Plays `games` games (None: until
    stopped). Watching, it plays one game and then waits for the page (Play again, another
    game, Loop, Stop) unless `loop` (default: the "casino_loop" setting) is on. Returns the
    last table played, with its statistics."""
    from fly_jjs.core.brain import get_brain_components
    from fly_jjs.core.config import ConfigManager
    from fly_jjs.core.dashboard import DEFAULT_PORT, BrainDashboard

    cfg = dict(ConfigManager.load_config())
    if fear is not None:
        cfg["fear"] = fear
    if game not in GAMES:
        raise ValueError(f"unknown game {game!r}; choose from {sorted(GAMES)}")
    components = get_brain_components()
    dash = None
    if dashboard:
        dash = BrainDashboard(components.brain, port=cfg.get("dashboard_port", DEFAULT_PORT))
        dash.start(open_browser=open_browser)
    fly = CasinoFly(components, cfg, learn=learn, seed=seed, readout=readout)
    path = memory_path or casino_memory_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fly.load(path)
    wallet = Wallet(money_path or wallet_path())
    session = {"loop": bool(cfg.get("casino_loop", False)) if loop is None else bool(loop), "game": game}
    tables = {}
    table = None
    played = 0
    print(f"[Casino] Fly #{wallet.generation} sits down with ${wallet.money:,} to play {GAMES[game].lower()}"
          + (f" against the {BOTS[bot]}" if game == "cards" and bot else "")
          + f". Fear strength {fly.fear.strength:g}. Stop with Ctrl+C" + (" or Stop on the page." if dash else "."))
    try:
        while games is None or played < games:
            name = session["game"]
            if name not in tables:
                tables[name] = make_table(name, components, cfg, fly, wallet, session, mode=mode, bot=bot,
                                          seed=None if seed is None else seed + len(tables), dashboard=dash,
                                          verbose=verbose)
            table = tables[name]
            table.play_game()
            played += 1
            if learn and played % 10 == 0:
                fly.save(path)
            if mode != "show":
                continue
            nxt = session.pop("next", None)
            if nxt is None and not session.get("loop"):
                nxt = table.wait()
            if nxt in GAMES:
                session["game"] = nxt
    except (KeyboardInterrupt, StopCasino):
        print("\n[Casino] Stopped.")
    finally:
        if learn:
            fly.save(path)
        wallet.save()
        if dash is not None:
            dash.stop()
    return table
