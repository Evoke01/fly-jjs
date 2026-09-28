import sys
import time
import os
import webbrowser
from fly_jjs.core.config import ConfigManager, DEVICE_TIERS, RESOLUTION_PRESETS

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt
    from rich import box
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_menu_header_panel():
    cfg = ConfigManager.load_config()
    tier = cfg.get("device_tier", "mid")
    res = cfg.get("resolution", "8x8")
    color = "Full RGB" if cfg.get("use_color", True) else "Grayscale"
    tier_name = DEVICE_TIERS.get(tier, {}).get('name', tier.title())

    header_text = """[bold green]
    ███████╗██╗     ██╗   ██╗         ██╗     ██╗███████╗
    ██╔════╝██║     ╚██╗ ██╔╝         ██║     ██║██╔════╝
    █████╗  ██║      ╚████╔╝          ██║     ██║███████╗
    ██╔══╝  ██║       ╚██╔╝      ██   ██║██   ██║╚════██║
    ██║     ███████╗   ██║       ╚█████╔╝╚█████╔╝███████║
    ╚═╝     ╚══════╝   ╚═╝        ╚════╝  ╚════╝ ╚══════╝[/bold green]
    [bold yellow]BIOLOGICAL REINFORCEMENT LEARNING SIMULATOR (v1.4.0)[/bold yellow]
    [cyan]Connecting Fruit Fly Connectome to Roblox (JJS / Sober)[/cyan]
    """
    
    status_str = f"[bold cyan]Mode:[/] {tier_name}  |  [bold cyan]Res:[/] {res}  |  [bold cyan]Color:[/] {color}"
    notes_str = "[bold red]⚠️ IMPORTANT NOTES:[/] [yellow]1. Shrink Roblox Window for Max FPS  |  2. Train 20+ Mins First[/]"

    content = f"{header_text}\n{status_str}\n{notes_str}"
    return Panel(content, border_style="bright_blue", box=box.ROUNDED)

def print_rich_menu():
    clear_screen()
    console.print(get_menu_header_panel())

    table = Table(title="[bold yellow]AVAILABLE OPERATION MODES[/bold yellow]", box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta")
    table.add_column("Option", justify="center", style="bold cyan", width=8)
    table.add_column("Mode Name", style="bold white", width=26)
    table.add_column("Simple Description", style="dim white")

    table.add_row("[ 1 ]", "🎮 Play Mode", "Autonomous fly combat & dopamine learning")
    table.add_row("[ 2 ]", "🧠 Train Mode", "Imitation trainer (Fly watches you play)")
    table.add_row("[ 3 ]", "⚡ Vision & Graphics", "Eye resolution (8x8-320x240), color & RAM tier")
    table.add_row("[ 4 ]", "📁 Profile Manager", "Save, switch, and backup brain memory files")
    table.add_row("[ 5 ]", "📊 Brain Analytics", "Inspect top action biases & learned synapses")
    table.add_row("[ 6 ]", "🗑️ Wipe Memory", "Reset fly brain weights (with auto-backup)")
    table.add_row("[ 7 ]", "🎵 Music Experiment", "Blast music to fly brain & live web dashboard")
    table.add_row("[ 8 ]", "🔬 Self Diagnostics", "Run connectome, retina, and memory self-test")
    table.add_row("[ 9 ]", "💡 Explainer Guide", "Beginner guide on how the fly brain plays JJS")
    table.add_row("[ M ]", "🧪 Manual Reward Mode", "Give manual Dopamine (+) or Punishment (-)")
    table.add_row("[ A ]", "🏟️ Arena", "Watch & train the fly in a simulated JJS fight")
    table.add_row("[ C ]", "🎯 Calibrate", "Show the fly your health bars & your character")
    table.add_row("[ L ]", "📡 Live Telemetry", "Watch a running Play/Train session (2nd terminal)")
    table.add_row("[ U ]", "🔄 Check Updates", "Pull latest updates directly from GitHub")
    table.add_row("[ 0 ]", "❌ Exit System", "Shut down FlyBrain simulator")

    console.print(table)
    console.print("[dim italic cyan]  Powered by connectome data from Janelia Research (HHMI) | Created by @FakeEvoke[/dim italic cyan]\n")

def print_fallback_menu():
    clear_screen()
    print("\x1b[38;5;46m" + r"""
    ███████╗██╗     ██╗   ██╗         ██╗     ██╗███████╗
    ██╔════╝██║     ╚██╗ ██╔╝         ██║     ██║██╔════╝
    █████╗  ██║      ╚████╔╝          ██║     ██║███████╗
    ██╔══╝  ██║       ╚██╔╝      ██   ██║██   ██║╚════██║
    ██║     ███████╗   ██║       ╚█████╔╝╚█████╔╝███████║
    ╚═╝     ╚══════╝   ╚═╝        ╚════╝  ╚════╝ ╚══════╝
    """ + "\x1b[0m")
    print("   \x1b[1m\x1b[38;5;226mBIOLOGICAL REINFORCEMENT LEARNING SIMULATOR (v1.4.0)\x1b[0m")
    print("   \x1b[38;5;51mConnecting Fruit Fly Connectome to Roblox (JJS / Sober)\x1b[0m\n")
    
    cfg = ConfigManager.load_config()
    tier = cfg.get("device_tier", "mid")
    res = cfg.get("resolution", "8x8")
    color = "Full RGB" if cfg.get("use_color", True) else "Grayscale"
    
    print(f"  Current Mode: {DEVICE_TIERS[tier]['name']} | Res: {res} | Visuals: {color}")
    print("  \x1b[38;5;208m⚠️ NOTES: 1. Shrink Roblox Window for Max FPS | 2. Train 20+ Mins First\x1b[0m\n")

    print("  [ 1 ] 🎮 Play Mode (Autonomous Fly Combat)")
    print("  [ 2 ] 🧠 Train Mode (Fly Watches You Play)")
    print("  [ 3 ] ⚡ Vision & Graphics Settings")
    print("  [ 4 ] 📁 Profile Manager (Save / Load Memories)")
    print("  [ 5 ] 📊 Brain Analytics & Synapses")
    print("  [ 6 ] 🗑️ Wipe Memory (Reset Fly Brain)")
    print("  [ 7 ] 🎵 Music Experiment & Web Dashboard")
    print("  [ 8 ] 🔬 Self Diagnostics")
    print("  [ 9 ] 💡 Explainer Guide")
    print("  [ M ] 🧪 Manual Reward Mode (Treat / Penalty)")
    print("  [ A ] 🏟️ Arena (Watch & Train in a Simulated Fight)")
    print("  [ C ] 🎯 Calibrate Health Bars & Your Character")
    print("  [ L ] 📡 Live Brain Telemetry (watch a running session)")
    print("  [ U ] 🔄 Check for Updates")
    print("  [ 0 ] ❌ Exit System\n")

def configure_modes():
    cfg = ConfigManager.load_config()
    while True:
        clear_screen()
        if RICH_AVAILABLE:
            table = Table(title="[bold yellow]⚡ Vision & Device Performance Engine[/bold yellow]", box=box.ROUNDED)
            table.add_column("Setting", style="bold cyan")
            table.add_column("Current Value", style="bold green")

            table.add_row("Device Tier Preset", f"{DEVICE_TIERS[cfg['device_tier']]['name']} ({DEVICE_TIERS[cfg['device_tier']]['min_ram']})")
            table.add_row("Resolution Grid", cfg['resolution'])
            table.add_row("Color Processing", 'Full RGB Color' if cfg['use_color'] else 'Grayscale')
            table.add_row("Pattern Recognition", 'Enabled' if cfg.get('pattern_recognition') else 'Disabled')
            table.add_row("Camera Target Lock", 'Enabled' if cfg.get('camera_lock_enabled') else 'Disabled')
            table.add_row("Brain Steps per Frame", str(cfg.get('brain_steps', 2)))
            console.print(table)

            console.print("\n[bold yellow]Hardware Tier Presets:[/] [1] Low-End (32x32 Gray)  [2] Mid-End (64x48 RGB)  [3] High-End (128x96 RGB)")
            console.print("[bold yellow]Custom Toggles:[/]       [4] Change Resolution  [5] Toggle RGB Color   [6] Toggle Target Lock   [7] Toggle Pattern Rec")
            console.print("[bold red][8] Back to Main Menu[/bold red]")
            sub_choice = Prompt.ask("\n[bold green]Select option[/bold green]").strip()
        else:
            print("\x1b[38;5;220m  [+] Vision Modes & Device Performance Engine\x1b[0m\n")
            print(f"  Current Device Tier: {DEVICE_TIERS[cfg['device_tier']]['name']}")
            print(f"  Current Resolution Grid: {cfg['resolution']}")
            print(f"  Color Processing: {'Full RGB Color' if cfg['use_color'] else 'Grayscale'}")
            print(f"  Brain Steps per Frame: {cfg.get('brain_steps', 2)}")
            print("\n  [1] Low-End (32x32 Gray)  [2] Mid-End (64x48 RGB)  [3] High-End (128x96 RGB)")
            print("  [4] Change Res  [5] Toggle Color  [6] Toggle Target Lock  [7] Toggle Pattern  [8] Back")
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

def arena_menu():
    from fly_jjs.core.arena import run_arena
    from fly_jjs.core.storage import ARENA_PROFILE, ARENA_WEIGHTS_PATH
    while True:
        clear_screen()
        print("\x1b[38;5;208m  [+] Arena: a simulated JJS fight to warm the fly up\x1b[0m\n")
        print("  The fly fights computer opponents with the same brain, eyes, instincts and")
        print("  learning it uses in Roblox. Its arena brain is kept separate from your game brain.\n")
        print("  [1] Watch the fly fight (3 fights, learning on)")
        print("  [2] Train fast without a window")
        print("  [3] Use the arena brain in the game (your current brain is backed up)")
        print("  [4] Back")
        sub = input("\n  Select option > ").strip()
        if sub == '1':
            run_arena(fights=3, learn=True, watch=True)
            input("\n  Press Enter to return...")
        elif sub == '2':
            raw = input("  How many fights? (Enter = 20): ").strip()
            fights = int(raw) if raw.isdigit() and int(raw) > 0 else 20
            raw = input("  Opponent difficulty 0.5-2.0 (Enter = 1.0): ").strip()
            try:
                difficulty = min(2.0, max(0.5, float(raw))) if raw else 1.0
            except ValueError:
                difficulty = 1.0
            results = run_arena(fights=fights, learn=True, watch=False, difficulty=difficulty)
            if results:
                wins = sum(r["won"] for r in results)
                print(f"\n  Won {wins}/{len(results)} fights. Arena brain saved.")
            input("\n  Press Enter to return...")
        elif sub == '3':
            if not os.path.exists(ARENA_WEIGHTS_PATH):
                print("\n  [!] No arena brain yet. Train it with [1] or [2] first.")
            else:
                from fly_jjs.core.profiles import ProfileManager
                ok, msg = ProfileManager.load_profile(ARENA_PROFILE)
                print(f"\n  {msg}")
            input("\n  Press Enter to return...")
        elif sub == '4':
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
        if RICH_AVAILABLE:
            print_rich_menu()
            choice = Prompt.ask("[bold green]Select Option[/bold green]").strip().lower()
        else:
            print_fallback_menu()
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
            from fly_jjs.core.storage import BACKUPS_DIR, WEIGHTS_PATH, create_backup_of_weights, wipe_memory
            if os.path.exists(WEIGHTS_PATH):
                print("\n  \x1b[38;5;196m[WARNING] This will reset the fly's active learned behaviors.\x1b[0m")
                confirm = input("  Are you sure? An automatic backup will be created first. (y/n): \x1b[38;5;196m").strip().lower()
                print("\x1b[0m", end="")
                if confirm == 'y':
                    create_backup_of_weights()
                    wipe_memory()
                    print(f"\n  [✓] Memory wiped successfully. Backup saved in {BACKUPS_DIR}")
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

        elif choice == 'm':
            clear_screen()
            print("\x1b[38;5;220m  [+] Initializing Manual Reward Mode...\x1b[0m")
            from fly_jjs.core.rl import run_rl
            run_rl(manual_mode=True)
            print("\n\x1b[38;5;239m" + "=" * 65 + "\x1b[0m")
            input("  \x1b[38;5;226mPress Enter to return to the main menu...\x1b[0m")

        elif choice == 'a':
            arena_menu()

        elif choice == 'c':
            clear_screen()
            from fly_jjs.core.calibrate import run_calibration
            run_calibration()
            input("\n  Press Enter to return to the main menu...")

        elif choice == 'l':
            clear_screen()
            print("  Tip: run this in a second terminal while Play/Train runs in the first one.")
            from fly_jjs.core.telemetry import run_telemetry
            run_telemetry()
            input("\n  Press Enter to return to the main menu...")

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
