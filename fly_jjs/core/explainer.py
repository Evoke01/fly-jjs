def show_simple_explainer():
    """Interactive guide explaining FlyBrain in simple, clear terms using Rich panels."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.markdown import Markdown

        console = Console()
        guide_text = """
# 🪰 FlyBrain × Roblox JJS Explainer Guide

### 🚀 What is this project?
Instead of using basic bots, we connected the **actual 3D brain wiring map (connectome)** of a real fruit fly to **Roblox Jujutsu Shenanigans**! The fly sees the screen, processes neurons, and learns how to fight.

---

### ⚡ Quick Tips for Peak Performance:
1. **Shrink Roblox Window:** Resize Roblox to the smallest size on screen to maximize capture FPS and reaction time.
2. **Train First (20+ Mins):** Run `[2] Train Mode` for at least 20 minutes so the fly learns your combat style and key combos.

---

### 🧠 Core Features & Upgrades:
- **👁️ Vision Grid (8x8 to 320x240):** Choose between grayscale and full RGB color modes.
- **🎯 Target Lock Camera:** Automatically tracks opponents and centers the camera using smooth mouse movement.
- **🔮 Pattern Predictor:** Detects opponent motion spikes to predict dashes and incoming attacks.
- **🧪 Dopamine Reward:**
  - Land hits / Kills  ➔ **Dopamine Spike** (+ Reward)
  - Take damage        ➔ **Dopamine Drop** (- Penalty)
- **🍬 Manual Reward Mode `[M]`:** Press `+` to treat or `-` to punish the fly directly while watching it fight!

---

*Pro Tip: Train the fly in `[2]` first, then unleash it in `[1] Play Mode`!*
"""
        console.clear()
        console.print(Panel(Markdown(guide_text), title="[bold green]💡 FLY BRAIN EXPLAINER GUIDE[/bold green]", border_style="cyan", padding=(1, 2)))
        console.print("\n[bold yellow]Press Enter to return to the main menu...[/bold yellow]")
        input()
    except ImportError:
        print("\n" + "=" * 65)
        print("  💡 FLY BRAIN EXPLAINER GUIDE: QUICK OVERVIEW")
        print("=" * 65)
        print("""
  🚀 WHAT IS THIS PROJECT?
  We connected a digital fruit fly connectome (130,000+ synapses) to Roblox JJS!

  ⚡ QUICK TIPS:
  1. Shrink Roblox window for highest FPS.
  2. Run [2] Train Mode for 20+ mins first.

  🧠 CORE FEATURES:
  • Vision Grid: 8x8 to 320x240 Full RGB
  • Target Lock Camera Tracking
  • Pattern Burst Predictor
  • Realtime Dopamine Reinforcement Learning
  • Manual Treat/Penalty Mode [M]
  """)
        input("  Press Enter to return to main menu...")
