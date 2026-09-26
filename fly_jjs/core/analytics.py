import os
import time
import numpy as np

USER_DIR = os.path.expanduser("~/.fly_jjs")
WEIGHTS_PATH = os.path.join(USER_DIR, "fly_weights.npy")

ACTION_NAMES = [
    "forward", "left", "back", "right",
    "melee",                                 # M1
    "skill1", "skill2", "skill3", "skill4",  # 1-4
    "dash",                                  # Q
    "block",                                 # F
    "special",                               # R
    "sprint",                                # W+W
    "awaken",                                # G
]

class BrainAnalytics:
    """Analyzes fly_weights.npy and reports connectivity & preference stats."""

    @staticmethod
    def analyze():
        if not os.path.exists(WEIGHTS_PATH):
            return {
                "exists": False,
                "message": "No brain memory file found (fly_weights.npy). Train or play first!"
            }

        weights = np.load(WEIGHTS_PATH)
        mtime = os.path.getmtime(WEIGHTS_PATH)
        last_modified = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
        size_kb = os.path.getsize(WEIGHTS_PATH) / 1024.0

        num_neurons, num_actions = weights.shape

        # Per-action cumulative bias & strength
        action_totals = np.sum(np.abs(weights), axis=0)
        action_means = np.mean(weights, axis=0)

        # Top dominant action
        top_action_idx = int(np.argmax(action_totals))
        top_action_name = ACTION_NAMES[top_action_idx] if top_action_idx < len(ACTION_NAMES) else f"Action {top_action_idx}"

        # Connectivity stats
        nonzero_synapses = int(np.count_nonzero(weights))
        total_synapses = num_neurons * num_actions
        connectivity_pct = (nonzero_synapses / total_synapses) * 100.0 if total_synapses > 0 else 0.0

        # Action biases breakdown
        biases = {}
        for i, name in enumerate(ACTION_NAMES[:num_actions]):
            biases[name] = {
                "total_weight": float(action_totals[i]),
                "mean_weight": float(action_means[i]),
            }

        return {
            "exists": True,
            "path": WEIGHTS_PATH,
            "last_modified": last_modified,
            "size_kb": size_kb,
            "num_neurons": num_neurons,
            "num_actions": num_actions,
            "top_action": top_action_name,
            "nonzero_synapses": nonzero_synapses,
            "connectivity_pct": connectivity_pct,
            "biases": biases,
            "weight_min": float(np.min(weights)),
            "weight_max": float(np.max(weights)),
            "weight_mean": float(np.mean(weights)),
            "weight_std": float(np.std(weights)),
        }
