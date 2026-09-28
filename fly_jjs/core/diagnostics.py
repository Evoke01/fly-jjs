import os
import numpy as np

from fly_jjs.core.storage import BACKUPS_DIR, LEARNER_PATH, PROFILES_DIR, WEIGHTS_PATH


def run_diagnostics():
    """Run a comprehensive diagnostic self-test of connectome & memory system."""
    print("\n" + "=" * 60)
    print("  🔬 FLY BRAIN DIAGNOSTIC SELF-TEST")
    print("=" * 60)

    # 1. Check Python & Libraries
    print("\n[Check 1/5] Checking Python Dependencies...")
    required_libs = ["numpy", "cv2", "mss", "flybrain"]
    for lib in required_libs:
        try:
            __import__(lib)
            print(f"  ✓ {lib}: OK")
        except ImportError:
            print(f"  ❌ {lib}: MISSING")

    # 2. Check Connectome Loading
    print("\n[Check 2/5] Testing Connectome & Neurons...")
    components = None
    try:
        from fly_jjs.core.rl import get_brain_components
        components = get_brain_components()
        print(f"  ✓ Connectome loaded: {len(components.dns)} descending neurons found")
        print(f"  ✓ Dopamine neurons: {len(components.reward_dans)} reward (PAM), "
              f"{len(components.punish_dans)} punishment (PPL1)")
    except Exception as e:
        print(f"  ❌ Connectome load error: {e}")

    # 3. Test the eyes and one brain cycle
    print("\n[Check 3/5] Testing Eyes & Brain Simulation Cycle...")
    if components is not None:
        try:
            from fly_jjs.core.config import ConfigManager
            from fly_jjs.core.vision import FlyEyes
            cfg = ConfigManager.load_config()
            eyes = FlyEyes(components.brain, cfg["resolution"], cfg["use_color"])
            print(f"  ✓ Eyes at {eyes.resolution}: {eyes.num_neurons} visual neurons")
            for line in eyes.describe():
                print(f"      {line}")
            frame = np.random.default_rng(0).integers(0, 255, (240, 320, 4), dtype=np.uint8)
            eyes.inject(frame)
            injections = eyes.inject(np.roll(frame, 8, axis=1))
            fired = components.brain.step(inject=injections)
            print(f"  ✓ Brain cycle step completed: {len(fired)} neurons fired with a test image")
        except Exception as e:
            print(f"  ❌ Brain step error: {e}")
    else:
        print("  ⚠️ Skipped (no neurons loaded)")

    # 4. Check Fly Memory / Weights File
    print("\n[Check 4/5] Checking Fly Memory (fly_weights.npy)...")
    if os.path.exists(WEIGHTS_PATH):
        try:
            w = np.load(WEIGHTS_PATH)
            print(f"  ✓ Memory file found: Shape={w.shape}, Non-zero values={np.count_nonzero(w)}")
            if os.path.exists(LEARNER_PATH):
                print("  ✓ Critic & action biases found (fly_weights_learner.npz)")
            else:
                print("  ℹ️ No critic file yet: older weights are converted on the next Play/Train run")
        except Exception as e:
            print(f"  ❌ Memory corrupt/unreadable: {e}")
    else:
        print("  ℹ️ No saved memory file yet (Fly is using blank slate)")

    # 5. Check Backups & Profiles
    print("\n[Check 5/5] Checking Backup & Profile Storage...")
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    os.makedirs(PROFILES_DIR, exist_ok=True)

    backups = [f for f in os.listdir(BACKUPS_DIR) if f.endswith(".npy")]
    profiles = os.listdir(PROFILES_DIR)
    print(f"  ✓ Backups available: {len(backups)}")
    print(f"  ✓ Saved profiles available: {len(profiles)}")

    print("\n" + "=" * 60)
    print("  ✅ DIAGNOSTIC SELF-TEST COMPLETE")
    print("=" * 60)
