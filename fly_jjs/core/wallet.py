"""The fly's money. Every fly sits down with $1,000; broke means shot.

Money lives across games (death match, slots, the races) and across runs: it is saved
next to what the casino flies have learned. When a fly is shot, whatever it had goes to
the house and the next fly gets a fresh $1,000.
"""
import json
import os
from collections import deque

START_MONEY = 1000


class Wallet:
    """The money of the fly at the table, and a record of all the flies before it."""

    def __init__(self, path=None):
        self.path = path
        self.generation = 1          # which fly this is
        self.money = START_MONEY
        self.peak = START_MONEY      # this fly's best
        self.richest = {"fly": 1, "money": START_MONEY}
        self.house = 0               # what the house has made from all the flies
        self.deaths = 0
        self.games = 0
        self.history = deque([START_MONEY], maxlen=120)   # this fly's money after each game
        self.ledger = deque(maxlen=8)                     # (what, amount), newest first
        if path:
            self.load()

    @property
    def broke(self):
        return self.money <= 0

    def change(self, amount, what):
        """Add (or, negative, take) money. Returns the amount that actually moved: nobody
        pays more than they have."""
        amount = int(max(amount, -self.money))
        self.money += amount
        self.house -= amount
        if amount:
            self.ledger.appendleft((what, amount))
        if self.money > self.peak:
            self.peak = self.money
        if self.money > self.richest["money"]:
            self.richest = {"fly": self.generation, "money": self.money}
        return amount

    def end_game(self):
        self.games += 1
        self.history.append(self.money)
        self.save()

    def died(self):
        """The fly was shot: the house keeps its money, and the next fly starts fresh."""
        self.house += self.money
        if self.money:
            self.ledger.appendleft((f"Fly #{self.generation} shot; the house keeps its money", -self.money))
        self.deaths += 1
        self.generation += 1
        self.money = START_MONEY
        self.house -= START_MONEY          # the house stakes the next fly
        self.peak = START_MONEY
        self.history = deque([START_MONEY], maxlen=120)
        self.save()

    def as_dict(self):
        return {"money": self.money, "start": START_MONEY, "peak": self.peak, "richest": dict(self.richest),
                "house": self.house, "generation": self.generation, "deaths": self.deaths,
                "history": list(self.history), "ledger": [list(e) for e in self.ledger]}

    # ---- saved between runs -----------------------------------------------------------

    def save(self):
        if not self.path:
            return
        data = {k: getattr(self, k) for k in ("generation", "money", "peak", "richest", "house", "deaths", "games")}
        data["history"] = list(self.history)
        tmp = self.path + ".tmp"
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, self.path)

    def load(self):
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (FileNotFoundError, ValueError, OSError):
            return False
        for key in ("generation", "money", "peak", "house", "deaths", "games"):
            if isinstance(data.get(key), int):
                setattr(self, key, data[key])
        if isinstance(data.get("richest"), dict):
            self.richest = {"fly": int(data["richest"].get("fly", 1)), "money": int(data["richest"].get("money", 0))}
        if isinstance(data.get("history"), list):
            self.history = deque((int(v) for v in data["history"][-120:]), maxlen=120)
        return True
