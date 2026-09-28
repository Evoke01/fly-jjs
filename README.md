# 🪰 FlyBrain × Roblox: Jujutsu Shenanigans (v1.2.0)

[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg?style=for-the-badge)](https://github.com/Evoke01/fly-jjs)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![YouTube](https://img.shields.io/badge/YouTube-@FakeEvoke-red?style=for-the-badge&logo=youtube)](https://www.youtube.com/@FakeEvoke)

Connect a real fruit fly's digital brain wiring (connectome) directly to **Roblox Jujutsu Shenanigans (JJS)**! Instead of traditional AI or basic bots, this project uses biological reinforcement learning and simulated neurons to see your screen, make fighting decisions, and play the game.

> **⚠️ IMPORTANT DISCLAIMER:**
> This simulation runs on a **mapped digital connectome** (a simulated 3D map of 130,000+ neurons and synapses based on biological research). **This is NOT a living biological brain, and NO real animals are involved.**

---

## ⚡ Quick Rules for Best Performance
1. **Shrink Roblox Window:** Make your Roblox window as small as possible on your desktop screen! Small windows drastically increase screen capture FPS and reaction time.
2. **Train First (20+ Mins):** Run `[2] Train Mode (Watcher)` for **20+ minutes** so the fly can learn your combos and combat style before playing on its own.

---

## 🏗️ System Flow

```
+-------------------+      +----------------------+      +----------------------+
|  Roblox JJS Game  | ---> |   Retina Visual Grid | ---> |  FlyBrain Connectome |
|  (Screen Capture) |      | (8x8 up to 320x240)  |      |  (130,000 Synapses)  |
+-------------------+      +----------------------+      +----------------------+
                                                                    |
                                                                    v
+-------------------+      +----------------------+      +----------------------+
| Game Character    | <--- | Realtime Motor Keys  | <--- | Dopamine Learning    |
| (Punch, Dash, M1) |      | (W, A, S, D, Q, F, M1|      | (Reinforcement Loop) |
+-------------------+      +----------------------+      +----------------------+
```

---

## 🎮 Easy Feature Overview

Here is what each mode in the menu does, explained in simple terms:

| Menu Option | Feature Name | What It Does (In Simple Terms) |
| :--- | :--- | :--- |
| **`[ 1 ]`** | 🎮 **Play Mode** | **Autonomous Fly Playing:** The fly takes full control of your character, fights opponents, and learns automatically. |
| **`[ 2 ]`** | 🧠 **Train Mode** | **Fly Watches You:** You play Roblox yourself while the fly watches your screen and keypresses to copy your combat style. |
| **`[ 3 ]`** | ⚡ **Vision & Graphics** | **Graphics & Device Settings:** Pick how sharp the fly's vision is (8x8 up to 320x240) and toggle RGB color modes. |
| **`[ 4 ]`** | 📁 **Profile Manager** | **Brain Memory Files:** Save, switch, or backup different trained fly brain profile files. |
| **`[ 5 ]`** | 📊 **Brain Analytics** | **Memory Inspector:** View the fly's favorite moves, active brain synapses, and learned habit scores. |
| **`[ 6 ]`** | 🗑️ **Wipe Memory** | **Reset Brain:** Reset the fly's memory back to a blank slate (creates an auto-backup first). |
| **`[ 7 ]`** | 🎵 **Music Experiment** | **Web Audio Dashboard:** Blast music into the fly's brain and monitor neural waves & dopamine on a live web browser dashboard. |
| **`[ 8 ]`** | 🔬 **Self Diagnostics** | **System Self-Test:** Tests your connectome setup, retina grid, and memory files to make sure everything works. |
| **`[ 9 ]`** | 💡 **Explainer Guide** | **Beginner Guide:** Quick hype guide breaking down how the connectome plays Roblox JJS. |
| **`[ M ]`** | 🧪 **Manual Reward Mode** | **Treat & Penalty Training (NEW):** Press `+` to give the fly a Dopamine treat (Good!) or `-` for Octopamine penalty (Bad!) while watching it fight. |
| **`[ L ]`** | 📡 **Live Telemetry** | **Lightweight Monitor (NEW):** View live brain firing rates, dopamine levels, and active motor outputs in a clean CLI dashboard. |
| **`[ U ]`** | 🔄 **Check for Updates** | **Pull Latest Code:** Fetch the latest updates directly from GitHub. |

---

## ⚙️ Hardware Tier Presets

You can select a preset that fits your PC performance in `[3] Vision & Graphics`:
- 🐢 **Low-End PC (4 GB RAM):** `8x8 Grayscale` — Ultra-fast FPS, minimal CPU/RAM usage.
- ⚖️ **Mid-End PC (8 GB RAM):** `192x144 Full RGB` — Balanced picture resolution and speed.
- 🚀 **High-End PC (16+ GB RAM):** `320x240 Full RGB` — High resolution visual tracking.

---

## 🛠️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Evoke01/fly-jjs.git
   cd fly-jjs
   ```

2. **Install required dependencies:**
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

## 📜 License & Creator Attribution
This project is open-source under the **MIT License**.

**Creator Attribution Requirement:**
If you showcase or use this project in a YouTube video, TikTok, stream, or public post, you **MUST** credit the original author by including a link to [@FakeEvoke](https://www.youtube.com/@FakeEvoke) in your description.
