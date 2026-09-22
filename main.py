import sys
import time
import os
import webbrowser

def clear_screen():
    # Properly clear the terminal screen across different OS
    os.system('cls' if os.name == 'nt' else 'clear')

def print_menu():
    clear_screen()
    print("=" * 65)
    print("      \x1b[38;5;46m🪰 FLY JJS - BIOLOGICAL REINFORCEMENT LEARNING\x1b[0m")
    print("=" * 65)
    print("\x1b[38;5;226m  Welcome to FlyBrain! Select a mode to start:\x1b[0m")
    print("\n  [1] \x1b[38;5;129m🎮 Play (RL Loop)\x1b[0m")
    print("      Let the fly play Jujutsu Shenanigans on its own.")
    print("      It will use dopamine-driven learning to improve.")
    print("\n  [2] \x1b[38;5;201m🧠 Train (Imitation Learning)\x1b[0m")
    print("      YOU play the game, and the fly watches.")
    print("      It learns to associate your actions with brain states.")
    print("\n  [3] \x1b[38;5;196m🗑️  Reset Memory (Delete Weights)\x1b[0m")
    print("      Wipe the fly's brain and start from absolute scratch.")
    print("\n  [4] \x1b[38;5;240m❌ Exit\x1b[0m")
    print("\n" + "=" * 65)
    print("  \x1b[38;5;240m* Connectome data from Janelia Research Campus (HHMI) *\x1b[0m")

def main():
    # Auto-open the explainer page once when the CLI starts
    explainer_path = os.path.abspath("explainer.html")
    if os.path.exists(explainer_path):
        webbrowser.open(f"file:///{explainer_path}")

    while True:
        print_menu()
        choice = input("\n  Select an option (1-4): ").strip()
        
        if choice == '1':
            clear_screen()
            print("\x1b[38;5;46m  [+] Starting RL Loop...\x1b[0m")
            from fly_jjs.core.rl import run_rl
            run_rl()
            print("\n" + "=" * 65)
            input("  \x1b[38;5;226mPress Enter to return to the main menu and clean up...\x1b[0m")
            
        elif choice == '2':
            clear_screen()
            print("\x1b[38;5;201m  [+] Starting Trainer...\x1b[0m")
            from fly_jjs.core.trainer import run_trainer
            run_trainer()
            print("\n" + "=" * 65)
            input("  \x1b[38;5;226mPress Enter to return to the main menu and clean up...\x1b[0m")
            
        elif choice == '3':
            weights_path = os.path.expanduser("~/.fly_jjs/fly_weights.npy")
            if os.path.exists(weights_path):
                print("\n  \x1b[38;5;196mWARNING: This will delete everything the fly has learned.\x1b[0m")
                confirm = input("  Are you sure? (y/n): ").strip().lower()
                if confirm == 'y':
                    os.remove(weights_path)
                    print("\n  [!] Memory wiped. The fly is now a blank slate.")
                else:
                    print("\n  [-] Cancelled.")
            else:
                print("\n  [!] No weights found. The fly's memory is already empty.")
            
            input("\n  Press Enter to return to the main menu...")
            
        elif choice == '4':
            print("\n  Goodbye!")
            sys.exit(0)
            
        else:
            print("\n  \x1b[38;5;196m[!] Invalid choice. Please select 1, 2, 3, or 4.\x1b[0m")
            time.sleep(1.5)

if __name__ == "__main__":
    # Enable ANSI escape sequences on Windows Command Prompt
    if os.name == 'nt':
        os.system('color')
    main()
