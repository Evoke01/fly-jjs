import os
import shutil
import time
import json

from fly_jjs.core.storage import PROFILES_DIR, WEIGHTS_PATH, create_backup_of_weights, memory_files

os.makedirs(PROFILES_DIR, exist_ok=True)


def _clean_name(profile_name):
    """Profile names become folder names: keep letters, digits, '_' and '-' only."""
    return "".join([c for c in (profile_name or "") if c.isalnum() or c in ("_", "-")]).strip()


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
        profile_name = _clean_name(profile_name)
        if not profile_name:
            return False, "Invalid profile name."

        if not os.path.exists(WEIGHTS_PATH):
            return False, "No active fly memory (fly_weights.npy) found to save!"

        pdir = os.path.join(PROFILES_DIR, profile_name)
        os.makedirs(pdir, exist_ok=True)
        mtarget = os.path.join(pdir, "metadata.json")

        for source, file_name in memory_files():
            target = os.path.join(pdir, file_name)
            if os.path.exists(source):
                shutil.copy2(source, target)
            elif os.path.exists(target):
                os.remove(target)  # don't pair these weights with a stale critic
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
        name = _clean_name(profile_name)
        pdir = os.path.join(PROFILES_DIR, name)
        wsource = os.path.join(pdir, "fly_weights.npy")
        if not name or not os.path.exists(wsource):
            return False, f"Profile '{profile_name}' not found."

        # Backup existing current weights before replacing
        create_backup_of_weights(tag="preload")

        for target, file_name in memory_files():
            source = os.path.join(pdir, file_name)
            if os.path.exists(source):
                shutil.copy2(source, target)
            elif os.path.exists(target):
                os.remove(target)  # profile predates the critic file: don't mix brains
        return True, f"Successfully loaded profile '{profile_name}' as active brain memory!"

    @staticmethod
    def delete_profile(profile_name):
        name = _clean_name(profile_name)
        pdir = os.path.join(PROFILES_DIR, name)
        if name and os.path.isdir(pdir):
            shutil.rmtree(pdir)
            return True, f"Deleted profile '{profile_name}'."
        return False, f"Profile '{profile_name}' does not exist."
