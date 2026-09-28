"""Where fly-jjs keeps its files (default ~/.fly_jjs; set FLY_JJS_HOME to move it)."""
import os
import shutil
import time

USER_DIR = os.path.abspath(os.path.expanduser(os.environ.get("FLY_JJS_HOME", "~/.fly_jjs")))
os.makedirs(USER_DIR, exist_ok=True)

WEIGHTS_FILE = "fly_weights.npy"
WEIGHTS_PATH = os.path.join(USER_DIR, WEIGHTS_FILE)
# Critic and action biases of the learner, saved next to the weights (see learning.py).
LEARNER_PATH = os.path.join(USER_DIR, "fly_weights_learner.npz")
CONFIG_PATH = os.path.join(USER_DIR, "config.json")
BACKUPS_DIR = os.path.join(USER_DIR, "backups")
PROFILES_DIR = os.path.join(USER_DIR, "profiles")
TELEMETRY_PATH = os.path.join(USER_DIR, "telemetry.json")


def memory_files():
    """The files that make up the fly's learned memory, as (path, file name) pairs."""
    return [(WEIGHTS_PATH, WEIGHTS_FILE), (LEARNER_PATH, os.path.basename(LEARNER_PATH))]


def create_backup_of_weights(tag="backup"):
    """Copy the current memory files into backups/ with a timestamp, if they exist."""
    if not os.path.exists(WEIGHTS_PATH):
        return None
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUPS_DIR, f"fly_weights_{tag}_{timestamp}.npy")
    try:
        shutil.copy2(WEIGHTS_PATH, backup_path)
        if os.path.exists(LEARNER_PATH):
            shutil.copy2(LEARNER_PATH, backup_path[:-len(".npy")] + "_learner.npz")
        print(f"[Backup] Created automatic backup at {backup_path}")
        return backup_path
    except Exception as e:
        print(f"[Backup] Failed to create backup: {e}")
        return None


def wipe_memory():
    """Delete the learned memory files. Returns True if anything was removed."""
    removed = False
    for path, _ in memory_files():
        if os.path.exists(path):
            os.remove(path)
            removed = True
    return removed
