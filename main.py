import sys
import time
import os
import webbrowser
from fly_jjs.core.config import ConfigManager, DEVICE_TIERS, RESOLUTION_PRESETS

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("\x1b[38;5;46m" + r"""
    ███████╗██╗     ██╗   ██╗         ██╗     ██╗███████╗
    ██╔════╝██║     ╚██╗ ██╔╝         ██║     ██║██╔════╝
    █████╗  ██║      ╚████╔╝          ██║     ██║███████╗
    ██╔══╝  ██║       ╚██╔╝      ██   ██║██   ██║╚════██║
    ██║     ███████╗   ██║       ╚█████╔╝╚█████╔╝███████║
    ╚═╝     ╚══════╝   ╚═╝        ╚════╝  ╚════╝ ╚══════╝
    """ + "\x1b[0m")
    print("\x1b[38;5;239m" + "═" * 65 + "\x1b[0m")
    print("   \x1b[1m\x1b[38;5;226mBIOLOGICAL REINFORCEMENT LEARNING SIMULATOR\x1b[0m")
    print("   \x1b[38;5;51mConnecting Fruit Fly Connectome to Roblox (JJS / Sober)\x1b[0m")
    print("\x1b[38;5;239m" + "═" * 65 + "\x1b[0m\n")

    # Important user notes & recommendations
    cfg = ConfigManager.load_config()
    tier = cfg.get("device_tier", "mid")
    res = cfg.get("resolution", "8x8")
    color = "Full RGB" if cfg.get("use_color", True) else "Grayscale"

    print("  \x1b[38;5;208m⚠️ IMPORTANT PERFORMANCE & TRAINING NOTES:\x1b[0m")
    print("  \x1b[38;5;222m1. RESIZE ROBLOX WINDOW TO THE SMALLEST POSSIBLE SIZE.\x1b[0m")
    print("  \x1b[38;5;222m2. AT LEAST 20+ MINUTES OF TRAINING DATA IS REQUIRED FOR GOOD RESULTS.\x1b[0m")
    print(f"  \x1b[38;5;117mCurrent Mode: {DEVICE_TIERS[tier]['name']} | Res: {res} | Visuals: {color}\x1b[0m")
    print("\x1b[38;5;239m" + "─" * 65 + "\x1b[0m\n")

def print_menu():
    clear_screen()
    print_header()
    print("  \x1b[38;5;15mSelect an operation mode:\x1b[0m\n")
    
    print("  \x1b[38;5;129m[ 1 ] 🎮  Play Mode (Autonomous RL)\x1b[0m")
    print("        \x1b[38;5;244mLet the fly brain take control and learn via dopamine.\x1b[0m\n")
    
    print("  \x1b[38;5;201m[ 2 ] 🧠  Train Mode (Imitation)\x1b[0m")
    print("        \x1b[38;5;244mPlay the game manually while the fly watches and learns.\x1b[0m\n")

    print("  \x1b[38;5;220m[ 3 ] ⚡  Modes & Vision Settings (Low/Mid/High Devices)\x1b[0m")
    print("        \x1b[38;5;244mConfigure resolution (8x8 to 320x240), RGB color, and RAM modes.\x1b[0m\n")

    print("  \x1b[38;5;226m[ 4 ] 📁  Profile Manager (Save / Load Brain Memories)\x1b[0m")
    print("        \x1b[38;5;244mSave, switch, and manage custom named fly brain profiles.\x1b[0m\n")

    print("  \x1b[38;5;51m[ 5 ] 📊  Brain Analytics & Weight Inspector\x1b[0m")
    print("        \x1b[38;5;244mInspect learned neural biases, top actions, and connectivity.\x1b[0m\n")
    
    print("  \x1b[38;5;196m[ 6 ] 🗑️   Wipe Memory\x1b[0m")
    print("        \x1b[38;5;244mDelete current weights file with auto-backup and reset to blank slate.\x1b[0m\n")
    
    print("  \x1b[38;5;213m[ 7 ] 🎵  Music Experiment\x1b[0m")
    print("        \x1b[38;5;244mMake the fly listen to custom music (or AIZO) and watch its brain.\x1b[0m\n")

    print("  \x1b[38;5;118m[ 8 ] 🔬  Run Brain Diagnostics\x1b[0m")
    print("        \x1b[38;5;244mRun a quick self-test of connectome, retina, and memory files.\x1b[0m\n")

    print("  \x1b[38;5;220m[ 9 ] 💡  Fly Brain Explainer Guide\x1b[0m")
    print("        \x1b[38;5;244mSuper simple, hype guide explaining how the fly brain plays JJS.\x1b[0m\n")

    print("  \x1b[38;5;111m[ U ] 🔄  Check for Updates\x1b[0m")
    print("        \x1b[38;5;244mPull the latest code and features from GitHub.\x1b[0m\n")
    
    print("  \x1b[38;5;240m[ 0 ] ❌  Exit System\x1b[0m\n")
    
    print("\x1b[38;5;239m" + "─" * 65 + "\x1b[0m")
    print("  \x1b[3;38;5;240mPowered by connectome data from Janelia Research (HHMI)\x1b[0m")
    print("  \x1b[3;38;5;240mCreated by @FakeEvoke on YouTube\x1b[0m")
    print("\x1b[38;5;239m" + "─" * 65 + "\x1b[0m")

def configure_modes():
    cfg = ConfigManager.load_config()
    while True:
        clear_screen()
        print("\x1b[38;5;220m  [+] Vision Modes & Device Performance Engine\x1b[0m\n")
        print(f"  Current Device Tier: \x1b[1m\x1b[38;5;46m{DEVICE_TIERS[cfg['device_tier']]['name']}\x1b[0m ({DEVICE_TIERS[cfg['device_tier']]['min_ram']})")
        print(f"  Current Resolution Grid: \x1b[1m\x1b[38;5;51m{cfg['resolution']}\x1b[0m")
        print(f"  Color Processing: \x1b[1m\x1b[38;5;213m{'Full RGB Color' if cfg['use_color'] else 'Grayscale (No Color)'}\x1b[0m")
        print(f"  Pattern Recognition: \x1b[1m{'Enabled' if cfg.get('pattern_recognition') else 'Disabled'}\x1b[0m")
        print(f"  Camera Target Locking: \x1b[1m{'Enabled' if cfg.get('camera_lock_enabled') else 'Disabled'}\x1b[0m")

        print("\n  \x1b[38;5;208mSelect Hardware Tier Preset:\x1b[0m")
        print("  [1] Low-End Mode (Min 4 GB RAM | 8x8 Grayscale | High FPS)")
        print("  [2] Mid-End Mode (Min 8 GB RAM | 192x144 Color | Balanced)")
        print("  [3] High-End Mode (Min 16 GB RAM | 320x240 Color | Precision)")
        print("\n  \x1b[38;5;208mCustom Granular Toggles:\x1b[0m")
        print("  [4] Change Resolution (8x8, 16x16, 32x32, 192x144, 320x240)")
        print("  [5] Toggle Color Mode (Full RGB vs No Color)")
        print("  [6] Toggle Target Lock Camera Tracking")
        print("  [7] Toggle Pattern Recognition")
        print("\n  [8] Back to Main Menu")

        sub_choice = input("\n  Select option > ").strip()
        if sub_choice == '1':
            ConfigManager.set_device_tier("low")
            cfg = ConfigManager.load_config()
            print("  [✓] Low-End mode applied!")
            time.sleep(1)
        elif sub_choice == '2':
            ConfigManager.set_device_tier("mid")
            cfg = ConfigManager.load_config()
            print("  [✓] Mid-End mode applied!")
            time.sleep(1)
        elif sub_choice == '3':
            ConfigManager.set_device_tier("high")
            cfg = ConfigManager.load_config()
            print("  [✓] High-End mode applied!")
            time.sleep(1)
        elif sub_choice == '4':
            print("\n  Available Resolutions: " + ", ".join(RESOLUTION_PRESETS.keys()))
            r_inp = input("  Enter resolution > ").strip()
            if r_inp in RESOLUTION_PRESETS:
                cfg["resolution"] = r_inp
                ConfigManager.save_config(cfg)
                print(f"  [✓] Resolution updated to {r_inp}!")
            else:
                print("  [!] Invalid resolution.")
            time.sleep(1)
        elif sub_choice == '5':
            cfg["use_color"] = not cfg["use_color"]
            ConfigManager.save_config(cfg)
            print(f"  [✓] Color set to: {'Full RGB' if cfg['use_color'] else 'Grayscale'}")
            time.sleep(1)
        elif sub_choice == '6':
            cfg["camera_lock_enabled"] = not cfg.get("camera_lock_enabled", True)
            ConfigManager.save_config(cfg)
            print(f"  [✓] Camera lock: {'Enabled' if cfg['camera_lock_enabled'] else 'Disabled'}")
            time.sleep(1)
        elif sub_choice == '7':
            cfg["pattern_recognition"] = not cfg.get("pattern_recognition", True)
            ConfigManager.save_config(cfg)
            print(f"  [✓] Pattern recognition: {'Enabled' if cfg['pattern_recognition'] else 'Disabled'}")
            time.sleep(1)
        elif sub_choice == '8':
            break

def main():
    if os.name == 'nt':
        os.system('color')
        
    explainer_path = os.path.abspath("explainer.html")
    if os.path.exists(explainer_path):
        try:
            webbrowser.open(f"file:///{explainer_path}")
        except Exception:
            pass

    while True:
        print_menu()
        choice = input("\n  \x1b[1m\x1b[38;5;46m>\x1b[0m ").strip().lower()
        
        if choice == '1':
            clear_screen()
            print("\x1b[38;5;46m  [+] Initializing Autonomous RL Loop...\x1b[0m")
            from fly_jjs.core.rl import run_rl
            run_rl()
            print("\n\x1b[38;5;239m" + "=" * 65 + "\x1b[0m")
            input("  \x1b[38;5;226mPress Enter to return to the main menu...\x1b[0m")
            
        elif choice == '2':
            clear_screen()
            print("\x1b[38;5;201m  [+] Initializing Imitation Trainer...\x1b[0m")
            from fly_jjs.core.trainer import run_trainer
            run_trainer()
            print("\n\x1b[38;5;239m" + "=" * 65 + "\x1b[0m")
            input("  \x1b[38;5;226mPress Enter to return to the main menu...\x1b[0m")

        elif choice == '3':
            configure_modes()

        elif choice == '4':
            clear_screen()
            print("\x1b[38;5;226m  [+] Profile Manager\x1b[0m\n")
            from fly_jjs.core.profiles import ProfileManager
            profiles = ProfileManager.list_profiles()
            print("  Available Fly Brain Profiles:")
            if not profiles:
                print("    (No saved profiles yet)")
            else:
                for p in profiles:
                    print(f"    • \x1b[1m{p['name']}\x1b[0m - Created: {p['created']} | Desc: {p['description']}")

            print("\n  Actions: [1] Save Current  [2] Load  [3] Delete  [4] Back")
            p_choice = input("  Select action > ").strip()
            if p_choice == '1':
                p_name = input("  Enter profile name: ").strip()
                p_desc = input("  Enter description: ").strip()
                ok, msg = ProfileManager.save_profile(p_name, p_desc)
                print(f"\n  {msg}")
            elif p_choice == '2':
                p_name = input("  Enter profile name to load: ").strip()
                ok, msg = ProfileManager.load_profile(p_name)
                print(f"\n  {msg}")
            elif p_choice == '3':
                p_name = input("  Enter profile name to delete: ").strip()
                ok, msg = ProfileManager.delete_profile(p_name)
                print(f"\n  {msg}")
            input("\n  Press Enter to return...")

        elif choice == '5':
            clear_screen()
            print("\x1b[38;5;51m  [+] Brain Analytics & Weight Inspector\x1b[0m\n")
            from fly_jjs.core.analytics import BrainAnalytics
            data = BrainAnalytics.analyze()
            if not data["exists"]:
                print(f"  [!] {data['message']}")
            else:
                print(f"  Memory File: {data['path']}")
                print(f"  Last Modified: {data['last_modified']} ({data['size_kb']:.1f} KB)")
                print(f"  Synapses Active: {data['nonzero_synapses']} / {data['num_neurons']*data['num_actions']} ({data['connectivity_pct']:.1f}%)")
                print(f"  Top Action Preference: \x1b[1m\x1b[38;5;46m{data['top_action'].upper()}\x1b[0m")
                print(f"  Weight Range: {data['weight_min']:.2f} to {data['weight_max']:.2f} (Mean: {data['weight_mean']:.3f})")
                print("\n  Top Action Biases:")
                sorted_biases = sorted(data["biases"].items(), key=lambda x: x[1]["total_weight"], reverse=True)
                for name, binfo in sorted_biases[:7]:
                    print(f"    - {name:>10}: total_weight = {binfo['total_weight']:+.2f}")
            input("\n  Press Enter to return...")

        elif choice == '6':
            weights_path = os.path.expanduser("~/.fly_jjs/fly_weights.npy")
            if os.path.exists(weights_path):
                print("\n  \x1b[38;5;196m[WARNING] This will reset the fly's active learned behaviors.\x1b[0m")
                confirm = input("  Are you sure? An automatic backup will be created first. (y/n): \x1b[38;5;196m").strip().lower()
                print("\x1b[0m", end="")
                if confirm == 'y':
                    from fly_jjs.core.trainer import create_backup_of_weights
                    create_backup_of_weights()
                    os.remove(weights_path)
                    print("\n  [✓] Memory wiped successfully. Backup saved in ~/.fly_jjs/backups/")
                else:
                    print("\n  [-] Operation cancelled.")
            else:
                print("\n  [!] No active weights found. The fly's memory is already empty.")
            
            input("\n  \x1b[38;5;244mPress Enter to return...\x1b[0m")
            
        elif choice == '7':
            clear_screen()
            print("\x1b[38;5;213m  [+] Initializing Music Experiment...\x1b[0m")
            yt_url = input("  Enter a YouTube URL (or press Enter for default AIZO): ").strip()
            from fly_jjs.core.music_experiment import run_music_experiment
            run_music_experiment(custom_url=yt_url if yt_url else None)

        elif choice == '8':
            clear_screen()
            from fly_jjs.core.diagnostics import run_diagnostics
            run_diagnostics()
            input("\n  Press Enter to return...")

        elif choice == '9':
            clear_screen()
            from fly_jjs.core.explainer import show_simple_explainer
            show_simple_explainer()

        elif choice in ('u', '99'):
            clear_screen()
            print("\n  \x1b[38;5;111m[+] Checking GitHub for updates...\x1b[0m\n")
            os.system("git pull")
            print("\n\x1b[38;5;239m" + "=" * 65 + "\x1b[0m")
            input("  \x1b[38;5;244mPress Enter to return to the menu...\x1b[0m")
            
        elif choice == '0':
            clear_screen()
            print("\n  \x1b[38;5;46mShutting down FlyBrain simulator... Goodbye!\x1b[0m\n")
            sys.exit(0)
            
        else:
            print("\n  \x1b[38;5;196m[!] Invalid command. Please try again.\x1b[0m")
            time.sleep(1)

if __name__ == "__main__":
    main()
