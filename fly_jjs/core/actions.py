"""What the fly can do in JJS, and which keys do it."""

ACTION_NAMES = [
    "forward", "left", "back", "right",
    "melee",                                 # M1
    "skill1", "skill2", "skill3", "skill4",  # 1-4
    "dash",                                  # Q
    "block",                                 # F
    "special",                               # R
    "sprint",                                # W+W
    "awaken",                                # G
    "jump",                                  # Space
]
NUM_ACTIONS = len(ACTION_NAMES)
ACTION_INDEX = {name: i for i, name in enumerate(ACTION_NAMES)}

# Keys held down for as long as the action is on (moving, blocking).
HELD_KEYS = {"forward": "w", "left": "a", "back": "s", "right": "d", "block": "f"}
# Keys tapped once when the action switches on.
TAPPED_KEYS = {
    "skill1": "1", "skill2": "2", "skill3": "3", "skill4": "4",
    "dash": "q", "special": "r", "awaken": "g", "jump": "space",
}
# "melee" is left-clicking at a combo rhythm; "sprint" is a W double-tap, then holding W.

MOVEMENT = ("forward", "left", "back", "right")
OPPOSITES = (("forward", "back"), ("left", "right"))   # pressing both does nothing
