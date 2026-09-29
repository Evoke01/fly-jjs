# 🪰 FlyBrain × Roblox: Jujutsu Shenanigans (v1.4.0)

[![Version](https://img.shields.io/badge/version-1.4.0-blue.svg?style=for-the-badge)](https://github.com/Evoke01/fly-jjs)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![YouTube](https://img.shields.io/badge/YouTube-@FakeEvoke-red?style=for-the-badge&logo=youtube)](https://www.youtube.com/@FakeEvoke)

Connect a real fruit fly's digital brain wiring (connectome) directly to **Roblox Jujutsu Shenanigans (JJS)**! Instead of traditional AI or basic bots, this project uses biological reinforcement learning and simulated neurons to see your screen, make fighting decisions, and play the game.

> **⚠️ IMPORTANT DISCLAIMER:**
> This simulation runs on a **mapped digital connectome** (the MaleCNS map of 166,700 neurons and 25.6 million connections, from biological research). **This is NOT a living biological brain, and NO real animals are involved.**

---

## ⚡ Quick Rules for Best Performance
1. **Shrink Roblox Window:** Make your Roblox window as small as possible on your desktop screen! Small windows drastically increase screen capture FPS and reaction time.
2. **Turn on Shift Lock** in Roblox, so moving the mouse turns the camera (that's how the fly aims).
3. **Calibrate once:** run `[C] Calibrate` and drag boxes around your health bar (and your character). The fly's rewards come from reading those bars.
4. **Train First (20+ Mins):** Run `[2] Train Mode (Watcher)` for **20+ minutes** so the fly can learn your combos and combat style before playing on its own. `[A] Arena` is a quick warm-up without Roblox.

---

## 🏗️ System Flow

```
+-------------------+      +------------------------+      +------------------------+
|  Roblox JJS Game  | ---> |  Compound Eyes +       | ---> |  FlyBrain Connectome   |
|  (Screen Capture) |      |  opponent tracker      |      |  (166,700 neurons)     |
+-------------------+      |  ~2,200 visual neurons |      +------------------------+
                           +------------------------+                  |
                                                                       v
+-------------------+      +------------------------+      +------------------------+
| Game Character    | <--- | Held keys, M1 combos,  | <--- | 59,310 neurons read +  |
| (Punch, Dash, M1) |      | camera tracking        |      | instincts + dopamine   |
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
| **`[ A ]`** | 🏟️ **Arena** | **Simulated Fight:** Watch or train the fly against computer opponents in a JJS-style arena, no Roblox needed. |
| **`[ C ]`** | 🎯 **Calibrate** | **Show the fly its HUD:** Drag boxes around your health bar, the opponent's, and your character, once. |
| **`[ B ]`** | 🧠 **3D Brain** | **Every Neuron, Live:** All 166,700 neurons in 3D in your browser, lighting up as they fire. Poke the fly with a looming shadow, a flash, or dopamine. |
| **`[ G ]`** | 🎰 **Casino** | **Gamble Money and Life:** $1,000 per fly, broke means shot. A card death match against a 3D tin robot (loser gets shot), a slot machine, and bets on totally random horse races. Terror meter read from its real fear circuit. |
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

## 🥊 How the Fly Fights

- **It reads 59,310 neurons.** Every frame the whole connectome (166,700 neurons) runs; the fly's decisions are read from everything downstream of its eyes: visual projection neurons, the central brain, ascending and descending neurons, the nerve cord and motor neurons (it used to read only 1,314 descending neurons).
- **It holds keys like a player.** W/A/S/D and block (F) stay held while the fly wants them, M1 clicks at a combo rhythm, skills/dash/jump are tapped, sprint is a W double-tap. (Before, every key was a one-frame tap, so the fly barely moved.) All keys are released when a session stops.
- **It aims.** An opponent tracker follows one target over time (colour, brightness and motion, with the camera's own turning cancelled out), ignores your own character and the HUD, and estimates distance and incoming attacks. The camera turns toward the opponent smoothly and sweeps to search when nobody is in view.
- **It has instincts.** Innate reflexes nudge its odds: close in when far, strike when in reach and facing them, block or dodge an incoming attack, circle to the side. Learning builds on top. (`"instincts"` in the config sets their strength; 0 turns them off.)
- **It is rewarded for real fighting.** Damage dealt and taken (read from the health bars, chip damage included) and knockouts. The old per-frame bonuses for blocking near the opponent are gone: in the arena the fly learned to hold block forever to farm them.

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

### `[A] Arena`
A JJS-style 1v1 simulator: M1 combos, skills on cooldowns, block, dash, jump, and an opponent that approaches, telegraphs its strikes and throws projectiles. The fly fights with the exact brain, eyes, instincts and learning it uses in Roblox. Watch it, train it fast without a window, then load the arena brain for the real game from the same menu. It's simpler than JJS, so treat it as a warm-up and fine-tune in the game.

### `[C] Calibrate`
Takes a screenshot of your game and asks you to drag boxes around your health bar (while full), the opponent's health bar (if shown), and your own character. Saved to the config; everything works with defaults until then.

### `[B] 🧠 3D Brain`
Opens a page in your browser (served on your own computer only, at `http://127.0.0.1:8765`) showing **every one of the 166,700 neurons** where it sits in the MaleCNS reconstruction, coloured by region: eyes, optic lobes, central brain, mushroom body (memory), reward and punishment dopamine neurons, descending neurons, nerve cord, motor neurons. Sensory neurons have their cell bodies outside the brain, so the data has no position for them; they are drawn on the organs they belong to (photoreceptors on the compound eyes, antennal receptors in the antennae, leg receptors along six legs), which draws the whole fly.

- **Glow = firing that is unusual for that neuron**, like ΔF/F in calcium imaging. At rest ~16% of neurons fire every 0.1 s, which would wash everything out; this way whatever the fly reacts to lights up. `Glow: every spike` shows raw spiking instead.
- Drag to turn, scroll to zoom, right-drag to pan. Click a region in the legend to hide it; pick a circuit (fear, reward, memory, motor commands) to highlight it.
- Buttons poke the fly: a **looming shadow** (its threat detectors fire, and through the connectome its giant-fibre escape neuron), a flash, a burst of reward or punishment dopamine.
- The arena can open the same view (`[A]` → `[5]`), the casino always does, and Play mode does when `"dashboard": true` is in the config.

### `[G] 🎰 Casino`
The fly gambles its money and its life. **Every fly sits down with $1,000, and broke means shot.** When a fly is shot the house keeps its money and the next fly takes the seat with a fresh $1,000, keeping what the others learned. The wallet, the richest fly so far and how many have died are saved between sessions. Three games:

- **Death match (cards):** **Higher or Lower** against a bot. The fly buys 10 chips at $10 each. A card is dealt; each player bets chips that the next card will be higher or lower (ties lose). Win and you gain the bet, lose and you lose it. A game is **three rounds**, the last for double stakes, and then **whoever has fewer chips gets shot**. Level after three? Sudden-death rounds decide it. Run out of chips and you are shot on the spot. A fly that survives cashes its chips out. The opponent is a bot (Rookie, Pro or Random), or nobody: alone, the fly plays the house and is shot if it ends with fewer chips than it started with.
- **Slots:** three reels. Three of a kind pays (**7-7-7 is the jackpot, 30× the bet**, about once in 140 spins), and so do two sevens or two cherries. Like a real machine it pays back 92% in the long run. After every spin the fly chooses to spin again ($10 or $50) or walk away with what it has left: the thrill of the lever and what it has learned a spin is worth pull it in, and its fear, which rises as its money drains away, pulls it off. The house makes it pull at least 3 times, and at most 25 a visit.
- **Horse races:** six horses, and the races are **totally random**: every horse has the same speed, stamina and luck, so each wins one race in six. The bookmaker doesn't know that. He prices every race from made-up form with a 25% margin, so a favourite is a terrible bet (about −47%) and a long shot a good one (about +59% at the longest odds). The fly reads the odds board, bets $50 or $200 on a horse and watches the race with its own eyes; its fear rises when its horse trails as the finish nears. A long shot (10/1 or more) coming in is a jackpot. Does it learn to back the long shots?
- **One game at a time.** After each game the page asks what next: **Play again**, another game, or **Loop** to keep playing by itself. Loop is off by default; it can also be turned on in the casino menu. **Train fast** plays many games at full speed without the page.
- **In 3D, next to its brain:** a wind-up tin robot across the card table (its dials show how it feels; it laughs when the fly is shot, and when it is shot its head pops off on a spring), a slot machine with spinning reels, a lever and a shower of coins, and a racetrack with a grandstand, a starting gate and six galloping racehorses with jockeys in silks, filmed alongside the pack and in slow motion at a close finish. Every model is built in code with three.js, which is bundled, so it works offline.
- **Sound:** the jackpot plays Hakari's jackpot theme with the 7-7-7 landing on its beat, and the gun is the Doom super shotgun. Browsers only play sound after you click the page once; **Sound** in the toolbar turns it off.
- **On the page:** the face-down card flips over on every reveal; when the fly survives, three cards flip to 7-7-7 and it hits the **JACKPOT**; when it loses, a crosshair locks onto its brain, the gun fires, and its brain goes grey and silent (the simulation of that fly really stops). The wallet panel charts its money game by game.
- **It sees the gun coming:** before it is shot the fly's eyes get a looming gun barrel, the stimulus its looming detectors (LPLC2) and giant-fibre escape neuron respond to, and you can watch them fire.
- **It sees each game with its own eyes:** the dealt card lights up on a board of 13 slots, ace far left and king far right, the way flies are shown bars in lab arenas; at the slots it sees the three reels, and at the races the odds board (a bar per horse, longer for longer odds) and then the horses running.
- **It learns what each choice is worth** from dopamine (prediction error = what happened − what it expected), separately for each game, and bets big only when it is confident. The page shows what it has learned: its strategy forming card by card, the pull of the lever against its fear, and which odds it backs.
- **It is afraid.** Danger (how near the end of the game is, how far behind it is, and how likely it thinks it is to lose on this card) drives its real fear circuit: the LC4 and LPLC2 threat and looming detectors and the PPL1 punishment neurons. The connectome carries that to the giant fibre (DNp01), the escape neuron. **The terror meter is how hard that circuit is firing**, and in 3D the circuit burns red. The more terrified it was when it bet, the more a loss teaches it. It bets big whenever it is confident, scared or not: in a death match, holding back just gets you shot (by the rules alone, a player that picks the likelier side 90% of the time beats the Rookie bot in 73% of games betting like this, and in 60% if it only bets big when near certain).
- Fear strength is a setting: 0 (fearless), 1 (normal), 2 (terrified), handy for comparing a fearless fly with a scared one.

Measured with the real connectome against the Rookie bot (two runs of 400 rounds, about 125 death matches each): after 300 rounds the fly picks the likelier side 89–92% of the time, and 92–97% after 400; it wins 63–67% of its bets (the best possible is 71%) and 60–72% of its death matches, so most flies live and plenty still get shot. Its learned chart comes to match the optimal strategy (higher on A–6, lower on 8–K) for nearly every card; the middle cards take longest, since the odds there are closest. "Fear" here means the activity of the neurons that fire when real flies escape threats, in a simulation; it is not a claim about what a fly feels.

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

The two sound clips in `fly_jjs/web/sounds` (Hakari's jackpot theme from *Jujutsu Kaisen* and the super shotgun from *Doom*) belong to their owners and are not covered by the MIT license. three.js, bundled in `fly_jjs/web/vendor`, is MIT-licensed (see `THREE_LICENSE.txt` there).

**Creator Attribution Requirement:**
If you showcase or use this project in a YouTube video, TikTok, stream, or public post, you **MUST** credit the original author by including a link to [@FakeEvoke](https://www.youtube.com/@FakeEvoke) in your description.
