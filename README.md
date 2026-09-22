# 🪰 FlyBrain × Roblox: Jujutsu Shenanigans

[![YouTube](https://img.shields.io/badge/YouTube-@FakeEvoke-red?style=for-the-badge&logo=youtube)](https://www.youtube.com/@FakeEvoke)

This project connects a scientifically accurate simulation of a fruit fly's brain to **Roblox (Jujutsu Shenanigans)**. Instead of using traditional algorithms, it uses the actual connectome (wiring diagram) of a fruit fly to perceive the screen and control the character.

By observing your gameplay or playing on its own, the fly learns to fight using real biological reinforcement learning (dopamine-driven plasticity).

## Features
- **Biologically Accurate RL**: Uses the `flybrain` library to simulate 130,000+ neurons and synapses.
- **Imitation Learning**: The fly watches you play and learns to associate visual stimuli with actions.
- **Interactive CLI**: Easily switch between playing and training modes right from your terminal.

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

### `[1] Play (RL Loop)`
Starts the reinforcement learning loop. 
- Open your Roblox window.
- The fly will take control of your keyboard and mouse. 
- It uses its dopamine neurons to learn what works (landing hits) and what doesn't (taking damage).
- **To stop:** Press `Q` in the "Fly Brain RL" window or move your mouse to the top-left corner of your screen (Failsafe).

### `[2] Train (Imitation Learning)`
Starts the supervised imitation learning mode.
- Open your Roblox window and play the game yourself.
- The fly will observe your key presses and screen visuals. 
- It will automatically update its weights (`fly_weights.npy`) to mimic your playstyle.
- **To stop:** Press `Q` or `ESC` to save the weights and exit.

---

## ⚠️ Notes
- The fly will save its learned weights in your home directory at `~/.fly_jjs/weights.npy`, so it keeps its memories even if you move the project folder.
- Ensure your Roblox window is visible and active when running either mode.

---

## 🔬 Scientific Acknowledgements
The simulated fruit fly brain is powered by the connectome mapping of the *Drosophila melanogaster*. Massive credit goes to the scientists and researchers at the **FlyEM Project at Janelia Research Campus (HHMI)** and **Google Research** who spent years mapping the 130,000 neurons and 50+ million synapses that make this simulation possible!

---

## 📜 License & Attribution
This project is open-source under the MIT License, with one strict condition for content creators:

**If you use this software in a YouTube video, TikTok, stream, or any other public media, you MUST credit the original creator by linking to [@FakeEvoke](https://www.youtube.com/@FakeEvoke) in your description.**
