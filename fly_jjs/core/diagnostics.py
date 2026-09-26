import sys
import os
import time
import numpy as np

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
    try:
        from flybrain import FlyBrain, FeatureDetectors
        brain = FlyBrain(device="cpu")
        fd = FeatureDetectors(brain)
        dns = brain.cells(["descending_neuron"])
        print(f"  ✓ Connectome loaded: {len(dns)} descending neurons found")
    except Exception as e:
        print(f"  ❌ Connectome load error: {e}")
        dns = []

    # 3. Test Brain Cycle Step
    print("\n[Check 3/5] Testing Brain Simulation Cycle...")
    if len(dns) > 0:
        try:
            # Simulate a dummy injection
            dummy_retina_r = np.random.rand(64)
            dummy_retina_b = np.random.rand(64)
            injections = []
            fired = brain.step(inject=injections)
            print(f"  ✓ Brain cycle step completed: {len(fired)} neurons fired in baseline test")
        except Exception as e:
            print(f"  ❌ Brain step error: {e}")
    else:
        print("  ⚠️ Skipped (no neurons loaded)")

    # 4. Check Fly Memory / Weights File
    print("\n[Check 4/5] Checking Fly Memory (fly_weights.npy)...")
    weights_path = os.path.expanduser("~/.fly_jjs/fly_weights.npy")
    if os.path.exists(weights_path):
        try:
            w = np.load(weights_path)
            print(f"  ✓ Memory file found: Shape={w.shape}, Non-zero values={np.count_nonzero(w)}")
        except Exception as e:
            print(f"  ❌ Memory corrupt/unreadable: {e}")
    else:
        print("  ℹ️ No saved memory file yet (Fly is using blank slate)")

    # 5. Check Backups & Profiles
    print("\n[Check 5/5] Checking Backup & Profile Storage...")
    backup_dir = os.path.expanduser("~/.fly_jjs/backups")
    profile_dir = os.path.expanduser("~/.fly_jjs/profiles")
    os.makedirs(backup_dir, exist_ok=True)
    os.makedirs(profile_dir, exist_ok=True)

    backups = os.listdir(backup_dir)
    profiles = os.listdir(profile_dir)
    print(f"  ✓ Backups available: {len(backups)}")
    print(f"  ✓ Saved profiles available: {len(profiles)}")

    print("\n" + "=" * 60)
    print("  ✅ DIAGNOSTIC SELF-TEST COMPLETE")
    print("=" * 60)
