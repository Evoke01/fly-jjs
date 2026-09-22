import sys
import time

def clear_screen():
    print("\033[2J\033[H", end="")

def print_menu():
    clear_screen()
    print("=" * 60)
    print("     🪰 FLY JJS - REINFORCEMENT LEARNING COMBAT BOT")
    print("=" * 60)
    print("\n  Welcome to FlyBrain! Select a mode to start:")
    print("\n  [1] 🎮 Play (RL Loop)")
    print("      Let the fly play Jujutsu Shenanigans on its own.")
    print("      It will use dopamine-driven learning to improve.")
    print("\n  [2] 🧠 Train (Imitation Learning)")
    print("      YOU play the game, and the fly watches.")
    print("      It learns to associate your actions with brain states.")
    print("\n  [3] ❌ Exit")
    print("\n" + "=" * 60)

def main():
    while True:
        print_menu()
        choice = input("\n  Select an option (1-3): ").strip()
        
        if choice == '1':
            print("\n  [+] Starting RL Loop...")
            from fly_jjs.core.rl import run_rl
            run_rl()
        elif choice == '2':
            print("\n  [+] Starting Trainer...")
            from fly_jjs.core.trainer import run_trainer
            run_trainer()
        elif choice == '3':
            print("\n  Goodbye!")
            sys.exit(0)
        else:
            print("\n  [!] Invalid choice. Please press 1, 2, or 3.")
            time.sleep(1)

if __name__ == "__main__":
    main()
