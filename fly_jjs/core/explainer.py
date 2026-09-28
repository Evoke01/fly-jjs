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
- **👁️ Compound Eyes (8x8 to 320x240):** The screen is split into a left and right eye and turned into brightness, darkness, motion and color maps, watched by ~2,400 of the fly's own visual neurons.
- **🎯 Target Lock Camera:** Follows one opponent (ignoring you and the HUD), turns the camera smoothly toward them and sweeps to search when nobody is in view. Turn on Shift Lock in Roblox.
- **🧠 59,310 Neurons Read:** The fly's decisions come from everything downstream of its eyes, not just its 1,314 descending neurons.
- **🥊 Fighting Instincts:** Close in when far, strike when in reach, block or dodge incoming attacks, circle to the side. Keys are held like a player holds them.
- **🔮 Pattern Predictor:** Detects opponent motion spikes to predict dashes and incoming attacks.
- **🧪 Dopamine = Surprise:**
  - Unexpected hit / Kill   ➔ **Dopamine Spike** on the fly's reward neurons
  - Unexpected damage       ➔ **Dopamine Dip** on its punishment neurons
  - The fly tries moves on purpose and keeps the ones that pay off.
- **🍬 Manual Reward Mode `[M]`:** Press `+` to treat or `-` to punish the fly while it fights (works while Roblox has focus)!
- **📡 Live Telemetry `[L]`:** Watch a running session's brain from a second terminal.
- **🏟️ Arena `[A]`:** Watch and train the fly in a simulated JJS fight, no Roblox needed.
- **🎯 Calibrate `[C]`:** Show the fly where your health bars and your character are, once.
- **🧠 3D Brain `[B]`:** All 166,700 neurons live in your browser; poke the fly and watch it react.
- **🎰 Casino `[G]`:** The fly gambles its life vs a bot, with a terror meter read from its real fear circuit.

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
  • Compound Eyes: 8x8 to 320x240, left/right eye, motion & color
  • Target Lock Camera Tracking
  • Pattern Burst Predictor
  • Dopamine = surprise (reward-prediction-error learning)
  • Reads 59,310 neurons; fighting instincts; held keys & camera tracking
  • Manual Treat/Penalty Mode [M], Live Telemetry [L], Arena [A], Calibrate [C]
  • 3D Brain [B]: every neuron live in the browser | Casino [G]: gambling with fear
  """)
        input("  Press Enter to return to main menu...")
