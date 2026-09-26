import os
import shutil
import time
import json

USER_DIR = os.path.expanduser("~/.fly_jjs")
PROFILES_DIR = os.path.join(USER_DIR, "profiles")
WEIGHTS_PATH = os.path.join(USER_DIR, "fly_weights.npy")
os.makedirs(PROFILES_DIR, exist_ok=True)

class ProfileManager:
    """Manages saving, loading, listing, and exporting named fly brain profiles."""

    @staticmethod
    def list_profiles():
        if not os.path.exists(PROFILES_DIR):
            return []
        profiles = []
        for name in os.listdir(PROFILES_DIR):
            pdir = os.path.join(PROFILES_DIR, name)
            wpath = os.path.join(pdir, "fly_weights.npy")
            mpath = os.path.join(pdir, "metadata.json")
            if os.path.isdir(pdir) and os.path.exists(wpath):
                meta = {}
                if os.path.exists(mpath):
                    try:
                        with open(mpath, "r") as f:
                            meta = json.load(f)
                    except Exception:
                        pass
                profiles.append({
                    "name": name,
                    "created": meta.get("created", "Unknown"),
                    "description": meta.get("description", "No description provided"),
                    "size_bytes": os.path.getsize(wpath)
                })
        profiles.sort(key=lambda x: x["name"])
        return profiles

    @staticmethod
    def save_profile(profile_name, description=""):
        profile_name = "".join([c for c in profile_name if c.isalnum() or c in ("_", "-")]).strip()
        if not profile_name:
            return False, "Invalid profile name."

        if not os.path.exists(WEIGHTS_PATH):
            return False, "No active fly memory (fly_weights.npy) found to save!"

        pdir = os.path.join(PROFILES_DIR, profile_name)
        os.makedirs(pdir, exist_ok=True)
        wtarget = os.path.join(pdir, "fly_weights.npy")
        mtarget = os.path.join(pdir, "metadata.json")

        shutil.copy2(WEIGHTS_PATH, wtarget)
        meta = {
            "name": profile_name,
            "description": description,
            "created": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(mtarget, "w") as f:
            json.dump(meta, f, indent=2)

        return True, f"Successfully saved profile '{profile_name}'."

    @staticmethod
    def load_profile(profile_name):
        pdir = os.path.join(PROFILES_DIR, profile_name)
        wsource = os.path.join(pdir, "fly_weights.npy")
        if not os.path.exists(wsource):
            return False, f"Profile '{profile_name}' not found."

        # Backup existing current weights before replacing
        if os.path.exists(WEIGHTS_PATH):
            backup_dir = os.path.join(USER_DIR, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            shutil.copy2(WEIGHTS_PATH, os.path.join(backup_dir, f"fly_weights_preload_{ts}.npy"))

        shutil.copy2(wsource, WEIGHTS_PATH)
        return True, f"Successfully loaded profile '{profile_name}' as active brain memory!"

    @staticmethod
    def delete_profile(profile_name):
        pdir = os.path.join(PROFILES_DIR, profile_name)
        if os.path.exists(pdir):
            shutil.rmtree(pdir)
            return True, f"Deleted profile '{profile_name}'."
        return False, f"Profile '{profile_name}' does not exist."
