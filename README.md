# 🪰 FlyBrain × Roblox: Jujutsu Shenanigans

[![YouTube](https://img.shields.io/badge/YouTube-@FakeEvoke-red?style=for-the-badge&logo=youtube)](https://www.youtube.com/@FakeEvoke)

This project connects a scientifically accurate simulation of a fruit fly's brain to **Roblox (Jujutsu Shenanigans)**. Instead of using traditional algorithms, it uses the actual connectome (wiring diagram) of a fruit fly to perceive the screen and control the character.

> **⚠️ IMPORTANT DISCLAIMER:**
> This simulation runs on a **mapped digital connectome**. It is purely a digital structure containing simulated neurons and synapses based on biological data. **This is NOT an actual biological brain, and it is NOT a sentient being.** No real flies are playing this game!

By observing your gameplay or playing on its own, the fly learns to fight using real biological reinforcement learning (dopamine-driven plasticity).

---

## ⚠️ GOLDEN RULES FOR BEST PERFORMANCE
1. **Minimize Roblox Window:** Resize your Roblox window to the smallest size possible on screen! This maximizes screen capture FPS and keeps the fly brain reacting ultra-fast.
2. **20+ Minutes Training Data:** Run `[2] Train Mode` for at least **20+ minutes** to build a solid training dataset for good combat results.

---

## ⚙️ HARDWARE & DEVICE MODES
You can select pre-configured hardware tiers in `[3] Modes & Vision Settings`:
- 🐢 **Low-End Mode (Min 4 GB RAM):** 8x8 Grayscale | Fast execution, minimal overhead.
- ⚖️ **Mid-End Mode (Min 8 GB RAM):** 192x144 Full RGB | Balanced resolution and performance.
- 🚀 **High-End Mode (Min 16 GB RAM):** 320x240 Full RGB | Precision target tracking.

---

## 🔥 KEY FEATURES
- **Biologically Accurate RL**: Uses the `flybrain` library to simulate 130,000+ neurons and synapses.
- **Experimental Modes & Resolutions**: Choose between `8x8`, `16x16`, `32x32`, `192x144`, and `320x240` resolution grids, plus Full RGB Color vs Grayscale toggles.
- **Pattern Recognition**: Analyzes opponent movement patterns over sliding time windows to predict dashes and bursts.
- **Target Lock & Camera Tracking**: Smooth mouse control automatically tracks and centers opponents in the fly's FOV.
- **Imitation Learning**: The fly watches you play and learns to associate visual stimuli with actions.
- **AIZO Music Experiment**: Blast the fly's brain with audio, tracked live through a sleek web dashboard monitoring neural activity, excitotoxicity, dopamine release, and emotional states via memes.
- **Interactive CLI**: Easily switch between playing, training, settings, and experimenting right from your terminal.

---

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Evoke01/fly-jjs.git
   cd fly-jjs
   ```

2. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🎮 How to Use

To start the interactive terminal menu, simply run:
```bash
python main.py
```

You will see the following options:

### `[1] Play (Autonomous RL)`
Starts the reinforcement learning loop. 
- Open your Roblox window.
- The fly will take control of your keyboard and mouse, using camera tracking, pattern recognition, and dopamine feedback.
- **To stop:** Press `Q` in the "Fly Brain RL" window or move your mouse to the top-left corner of your screen (Failsafe).

### `[2] Train (Imitation Learning)`
Starts the supervised imitation learning mode.
- Open your Roblox window and play the game yourself.
- The fly will observe your key presses and screen visuals.
- Displays a real-time progress bar toward the recommended 20-minute mark.
- **To stop:** Press `Q` or `ESC` to save the weights and exit.

### `[3] Modes & Vision Settings`
Configure hardware tier presets (Low/Mid/High), resolutions (8x8 to 320x240), RGB color toggles, target lock sensitivity, and pattern recognition.

### `[4] Profile Manager`
Save, switch, and manage custom named fly brain profiles.

### `[5] Brain Analytics`
Inspect learned neural biases, top actions, weight ranges, and connectivity percentages.

### `[6] Wipe Memory`
Deletes the current `fly_weights.npy` file with auto-backup, resetting the fly to a blank slate.
### `[3] 📁 Profile Manager`
Save, switch, and manage custom named fly brain profiles.

### `[4] 📊 Brain Analytics & Weight Inspector`
Inspect learned neural biases, top actions, and connectivity.

### `[5] 🗑️ Wipe Memory`
Deletes the current `fly_weights.npy` file, saving an automatic backup, and returning the fly to a blank slate.

### `[6] 🎵 Music Experiment`
Runs the experimental audio stimulation module.
- You can **paste your own custom YouTube URL** or press Enter to use the default extreme bass track (AIZO).
- The script automatically downloads the audio, analyzes the frequencies, and injects them directly into the fly's simulated auditory and mechanosensory systems.
- Open your browser to `http://localhost:9876` to view the **Live Neural Dashboard**, which tracks brain activity, neural death (from excitotoxicity), and dopamine levels in real-time.

### `[7] 🔬 Run Brain Diagnostics`
Run a quick self-test of the connectome, retina, and memory files.

### `[8] 💡 Fly Brain Explainer Guide`
Opens a simple, hype guide explaining how the fly brain plays JJS.

### `[9] 🔄 Check for Updates`
Pulls the latest code and features from the GitHub repository automatically.

---

### `[7] 🎵 Music Experiment`
Runs the experimental audio stimulation module with a live web dashboard at `http://localhost:9876`.

### `[8] Run Brain Diagnostics`
Self-test connectome components, retina inputs, and memory file integrity.

### `[9] Fly Brain Explainer Guide`
Interactive hype guide explaining how the fly brain plays JJS.

---

## 📜 License & Attribution
This project is open-source under the MIT License, with one strict condition for content creators:

**If you use this software in a YouTube video, TikTok, stream, or any other public media, you MUST credit the original creator by linking to [@FakeEvoke](https://www.youtube.com/@FakeEvoke) in your description.**
