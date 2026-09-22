import sys
import time
import os
import webbrowser

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("\x1b[38;5;46m" + r"""
    ███████╗██╗     ██╗   ██╗    ██╗██╗███████╗
    ██╔════╝██║     ╚██╗ ██╔╝    ██║██║██╔════╝
    █████╗  ██║      ╚████╔╝     ██║██║███████╗
    ██╔══╝  ██║       ╚██╔╝ ██   ██║██║╚════██║
    ██║     ███████╗   ██║  ╚█████╔╝██║███████║
    ╚═╝     ╚══════╝   ╚═╝   ╚════╝ ╚═╝╚══════╝
    """ + "\x1b[0m")
    print("\x1b[38;5;239m" + "═" * 60 + "\x1b[0m")
    print("   \x1b[1m\x1b[38;5;226mBIOLOGICAL REINFORCEMENT LEARNING SIMULATOR\x1b[0m")
    print("\x1b[38;5;239m" + "═" * 60 + "\x1b[0m\n")

def print_menu():
    clear_screen()
    print_header()
    print("  \x1b[38;5;15mSelect an operation mode:\x1b[0m\n")
    
    print("  \x1b[38;5;129m[ 1 ] 🎮  Play Mode (Autonomous RL)\x1b[0m")
    print("        \x1b[38;5;244mLet the fly brain take control and learn via dopamine.\x1b[0m\n")
    
    print("  \x1b[38;5;201m[ 2 ] 🧠  Train Mode (Imitation)\x1b[0m")
    print("        \x1b[38;5;244mPlay the game manually while the fly watches and learns.\x1b[0m\n")
    
    print("  \x1b[38;5;196m[ 3 ] 🗑️   Wipe Memory\x1b[0m")
    print("        \x1b[38;5;244mDelete the weights.npy file and start from a blank slate.\x1b[0m\n")
    
    print("  \x1b[38;5;240m[ 4 ] ❌  Exit System\x1b[0m\n")
    
    print("\x1b[38;5;239m" + "─" * 60 + "\x1b[0m")
    print("  \x1b[3;38;5;240mPowered by connectome data from Janelia Research (HHMI)\x1b[0m")
    print("\x1b[38;5;239m" + "─" * 60 + "\x1b[0m")

def main():
    if os.name == 'nt':
        os.system('color')
        
    explainer_path = os.path.abspath("explainer.html")
    if os.path.exists(explainer_path):
        webbrowser.open(f"file:///{explainer_path}")

    while True:
        print_menu()
        choice = input("\n  \x1b[1m\x1b[38;5;46m>\x1b[0m ").strip()
        
        if choice == '1':
            clear_screen()
            print("\x1b[38;5;46m  [+] Initializing Autonomous RL Loop...\x1b[0m")
            from fly_jjs.core.rl import run_rl
            run_rl()
            print("\n\x1b[38;5;239m" + "=" * 60 + "\x1b[0m")
            input("  \x1b[38;5;226mPress Enter to return to the main menu...\x1b[0m")
            
        elif choice == '2':
            clear_screen()
            print("\x1b[38;5;201m  [+] Initializing Imitation Trainer...\x1b[0m")
            from fly_jjs.core.trainer import run_trainer
            run_trainer()
            print("\n\x1b[38;5;239m" + "=" * 60 + "\x1b[0m")
            input("  \x1b[38;5;226mPress Enter to return to the main menu...\x1b[0m")
            
        elif choice == '3':
            weights_path = os.path.expanduser("~/.fly_jjs/fly_weights.npy")
            if os.path.exists(weights_path):
                print("\n  \x1b[38;5;196m[WARNING] This will permanently delete the fly's learned behaviors.\x1b[0m")
                confirm = input("  Are you sure? (y/n): \x1b[38;5;196m").strip().lower()
                print("\x1b[0m", end="")
                if confirm == 'y':
                    os.remove(weights_path)
                    print("\n  [✓] Memory wiped successfully.")
                else:
                    print("\n  [-] Operation cancelled.")
            else:
                print("\n  [!] No weights found. The fly's memory is already empty.")
            
            input("\n  \x1b[38;5;244mPress Enter to return...\x1b[0m")
            
        elif choice == '4':
            clear_screen()
            print("\n  \x1b[38;5;46mShutting down FlyBrain simulator... Goodbye!\x1b[0m\n")
            sys.exit(0)
            
        else:
            print("\n  \x1b[38;5;196m[!] Invalid command.\x1b[0m")
            time.sleep(1)

if __name__ == "__main__":
    main()
