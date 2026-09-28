# 🪰 FlyBrain × Roblox: Jujutsu Shenanigans (v1.3.0)

[![Version](https://img.shields.io/badge/version-1.3.0-blue.svg?style=for-the-badge)](https://github.com/Evoke01/fly-jjs)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![YouTube](https://img.shields.io/badge/YouTube-@FakeEvoke-red?style=for-the-badge&logo=youtube)](https://www.youtube.com/@FakeEvoke)

Connect a real fruit fly's digital brain wiring (connectome) directly to **Roblox Jujutsu Shenanigans (JJS)**! Instead of traditional AI or basic bots, this project uses biological reinforcement learning and simulated neurons to see your screen, make fighting decisions, and play the game.

> **⚠️ IMPORTANT DISCLAIMER:**
> This simulation runs on a **mapped digital connectome** (the MaleCNS map of 166,700 neurons and 25.6 million connections, from biological research). **This is NOT a living biological brain, and NO real animals are involved.**

---

## ⚡ Quick Rules for Best Performance
1. **Shrink Roblox Window:** Make your Roblox window as small as possible on your desktop screen! Small windows drastically increase screen capture FPS and reaction time.
2. **Train First (20+ Mins):** Run `[2] Train Mode (Watcher)` for **20+ minutes** so the fly can learn your combos and combat style before playing on its own.

---

## 🏗️ System Flow

```
+-------------------+      +------------------------+      +------------------------+
|  Roblox JJS Game  | ---> |  Compound Eyes          | ---> |  FlyBrain Connectome   |
|  (Screen Capture) |      |  L/R eye, ~2,400 visual |      |  (166,700 neurons)     |
+-------------------+      |  neurons, 8x8-320x240   |      +------------------------+
                           +------------------------+                  |
                                                                       v
+-------------------+      +------------------------+      +------------------------+
| Game Character    | <--- | Realtime Motor Keys    | <--- | Descending neurons +   |
| (Punch, Dash, M1) |      | (W, A, S, D, Q, F, M1) |      | dopamine learning      |
+-------------------+      +------------------------+      +------------------------+
```

---

## 🎮 Easy Feature Overview

Here is what each mode in the menu does, explained in simple terms:

| Menu Option | Feature Name | What It Does (In Simple Terms) |
| :--- | :--- | :--- |
| **`[ 1 ]`** | 🎮 **Play Mode** | **Autonomous Fly Playing:** The fly takes full control of your character, fights opponents, and learns automatically. |
| **`[ 2 ]`** | 🧠 **Train Mode** | **Fly Watches You:** You play Roblox yourself while the fly watches your screen and keypresses to copy your combat style. |
| **`[ 3 ]`** | ⚡ **Vision & Graphics** | **Graphics & Device Settings:** Pick how sharp the fly's vision is (8x8 up to 320x240), color, and your PC tier. |
| **`[ 4 ]`** | 📁 **Profile Manager** | **Brain Memory Files:** Save, switch, or backup different trained fly brain profile files. |
| **`[ 5 ]`** | 📊 **Brain Analytics** | **Memory Inspector:** View the fly's favorite moves, active brain synapses, and learned habit scores. |
| **`[ 6 ]`** | 🗑️ **Wipe Memory** | **Reset Brain:** Reset the fly's memory back to a blank slate (creates an auto-backup first). |
| **`[ 7 ]`** | 🎵 **Music Experiment** | **Web Audio Dashboard:** Blast music into the fly's brain and monitor neural waves & dopamine on a live web browser dashboard. |
| **`[ 8 ]`** | 🔬 **Self Diagnostics** | **System Self-Test:** Tests your connectome setup, the fly's eyes, and memory files to make sure everything works. |
| **`[ 9 ]`** | 💡 **Explainer Guide** | **Beginner Guide:** Quick hype guide breaking down how the connectome plays Roblox JJS. |
| **`[ M ]`** | 🧪 **Manual Reward Mode** | **Treat & Penalty Training:** While the fly fights, press `+` to give it a dopamine treat (Good!) or `-` for a penalty (Bad!). Works while Roblox has focus. |
| **`[ L ]`** | 📡 **Live Telemetry** | **Brain Monitor:** Open in a second terminal to watch a running Play/Train session live: motor outputs, dopamine, vision and rewards. |
| **`[ U ]`** | 🔄 **Check for Updates** | **Pull Latest Code:** Fetch the latest updates directly from GitHub. |

---

## ⚙️ Hardware Tier Presets

You can select a preset that fits your PC performance in `[3] Vision & Graphics`:
- 🐢 **Low-End PC (4 GB RAM):** `32x32 Grayscale`, 1 brain step per frame — fastest, minimal CPU/RAM usage.
- ⚖️ **Mid-End PC (8 GB RAM):** `64x48 Full RGB`, 2 brain steps per frame — balanced detail and speed.
- 🚀 **High-End PC (16+ GB RAM):** `128x96 Full RGB`, 3 brain steps per frame — sharpest vision, most brain time.

Each brain step simulates 20 ms of the fly's brain. More steps per game frame give its motor neurons more spikes to go on, so more of what it sees reaches its decisions (in our tests, 2 steps instead of 1 raised how well the fly's motor neurons track where the opponent is from R² 0.43 to 0.57).

---

## 👁️ How the Fly Sees

Older versions copied the first 64 pixels of the screen onto 128 neurons. Above 8x8 that was only a thin strip at the very top of the screen, and the signal was so strong it drowned out everything else the brain knew. Now the fly has proper compound eyes:

1. The screen is shrunk to your chosen grid (8x8 up to 320x240).
2. It is split into maps the way a fly's early visual system does it: **brighter than the surroundings**, **darker than the surroundings**, **motion**, and in color mode **red** and **blue**.
3. The left half of the screen goes to the fly's **left eye** and the right half to its **right eye**.
4. Each map drives its own types of the fly's real visual neurons (about 2,400 in color mode). Every neuron watches its own patch of the screen, and these types were picked because they connect straight into the fly's descending (motor) neurons.
5. Only what **stands out** gets through (a flat floor stays quiet, an opponent or a flash does not), and the eyes adapt to dark and bright scenes on their own.

On a test arena, the fly's motor neurons now carry much more about the opponent than before: see the pull request for the numbers.

## 🧪 How the Fly Learns

- **Dopamine = surprise.** The fly keeps a running guess of how well the fight is going. A hit it didn't expect releases dopamine on its real reward neurons (PAM); damage it didn't see coming drives its punishment neurons (PPL1). Rewards it already expected teach nothing new.
- **It tries things on purpose.** Every frame each move is a weighted coin flip, so the fly keeps exploring instead of spamming one key forever.
- **Credit where it's due.** A short memory trace links a reward to the moves made just before it, even if the hit lands a moment later.
- **Train and Play teach the same brain.** Train Mode fits the fly to the keys you press (including when you *don't* attack), and Play Mode keeps improving that same policy from rewards.

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

The first run downloads the connectome (~260 MB, once) into `~/fly-data`.

---

## 🎮 How to Use

To start the interactive terminal menu, simply run:
```bash
python main.py
```

### `[1] Play (Autonomous RL)`
Starts the reinforcement learning loop.
- Open your Roblox window. When the countdown appears, click on Roblox.
- The fly will take control of your keyboard and mouse, using camera tracking, pattern recognition, and dopamine feedback.
- **To stop:** Press `ESC` in the "Fly Brain RL" window or move your mouse to the top-left corner of your screen (Failsafe). (Not `Q`: the fly presses `Q` itself to dash.)

### `[2] Train (Imitation Learning)`
Starts the supervised imitation learning mode.
- Open your Roblox window and play the game yourself.
- The fly will observe your key presses and screen visuals, and shows how well it already predicts your moves.
- Learning pauses automatically while you don't touch the keyboard or mouse (menus, AFK).
- Displays a real-time progress bar toward the recommended 20-minute mark.
- **To stop:** Press `ESC` in the "Fly Trainer" window to save the weights and exit.

### `[3] Vision & Graphics`
Configure hardware tier presets (Low/Mid/High), the vision grid (8x8 to 320x240), RGB color, target lock, and pattern recognition.

### `[4] Profile Manager`
Save, switch, and manage custom named fly brain profiles.

### `[5] Brain Analytics`
Inspect learned neural biases, top actions, weight ranges, and connectivity percentages.

### `[6] Wipe Memory`
Deletes the current brain memory with auto-backup, resetting the fly to a blank slate.

### `[7] 🎵 Music Experiment`
Runs the experimental audio stimulation module.
- You can **paste your own custom YouTube URL** or press Enter to use the default extreme bass track (AIZO).
- The script automatically downloads the audio, analyzes the frequencies, and injects them into the fly's simulated brain.
- Open your browser to `http://localhost:9876` to view the **Live Neural Dashboard**, which tracks brain activity, neural death (from excitotoxicity), and dopamine levels in real-time.

### `[8] Run Brain Diagnostics`
Self-test connectome components, the fly's eyes, dopamine neurons, and memory file integrity.

### `[9] Fly Brain Explainer Guide`
Interactive hype guide explaining how the fly brain plays JJS.

### `[M] Manual Reward Mode`
Play Mode where you are the judge: press `+` (or `=`) for a treat and `-` for a penalty while the fly fights. The keys work while Roblox has focus.

### `[L] Live Telemetry`
Run `python main.py` in a **second terminal** and pick `[L]` while Play, Manual or Train mode runs in the first one.

### `[U] Check for Updates`
Pulls the latest code and features from the GitHub repository automatically.

---

## 🧰 For Developers

Run the tests with:
```bash
pip install pytest
python -m pytest
```
Tests use a throwaway data folder, so they never touch your trained brain in `~/.fly_jjs` (set `FLY_JJS_HOME` to move that folder). The connectome integration tests run only if the brain data is already downloaded.

---

## 📜 License & Creator Attribution
This project is open-source under the **MIT License**.

**Creator Attribution Requirement:**
If you showcase or use this project in a YouTube video, TikTok, stream, or public post, you **MUST** credit the original author by including a link to [@FakeEvoke](https://www.youtube.com/@FakeEvoke) in your description.
