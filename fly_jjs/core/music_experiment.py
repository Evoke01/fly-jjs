import time
import os
import sys
import json
import socket
import threading
import subprocess
import numpy as np
from collections import deque

# =====================================================
# FLY BRAIN × MUSIC EXPERIMENT
#
# Experiment: Make a fruit fly brain listen to AIZO
# (extreme bass/electronic music) and observe:
#   - Which neurons fire in response to audio
#   - Does the brain show stress/damage patterns?
#   - How does sustained bombardment affect neural stability?
#   - Emotional state tracking via dopamine/arousal
#
# The audio frequencies are injected into the fly's
# auditory neurons (Johnston's Organ → AMMC pathway)
# as well as vibration-sensitive mechanosensory neurons.
#
# A separate HTML dashboard visualizes the brain in
# real-time via WebSocket.
# =====================================================

print("=" * 60)
print("  FLY BRAIN × MUSIC EXPERIMENT")
print("  'What happens when a fly listens to AIZO?'")
print("=" * 60)

# ── AUDIO SETUP ──────────────────────────────────────
YOUTUBE_URL = "https://youtu.be/zz2a9Q2Wru0?si=8yQpc-Fdlc3me4s8"
AUDIO_DIR = os.path.expanduser("~/.fly_jjs/audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
AUDIO_FILE = os.path.join(AUDIO_DIR, "aizo_experiment.wav")

DATA_DIR = os.path.expanduser("~/.fly_jjs/experiment_data")
os.makedirs(DATA_DIR, exist_ok=True)


def download_audio():
    """Download audio from YouTube using yt-dlp."""
    if os.path.exists(AUDIO_FILE):
        print(f"[Audio] Found cached audio: {AUDIO_FILE}")
        return True

    print(f"[Audio] Downloading from YouTube...")
    print(f"[Audio] URL: {YOUTUBE_URL}")

    try:
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "-x",  # Extract audio
            "--audio-format", "wav",
            "--audio-quality", "0",
            "-o", AUDIO_FILE.replace(".wav", ".%(ext)s"),
            "--no-playlist",
            YOUTUBE_URL,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            # Try alternative invocation
            cmd2 = [
                "yt-dlp",
                "-x", "--audio-format", "wav",
                "-o", AUDIO_FILE.replace(".wav", ".%(ext)s"),
                "--no-playlist",
                YOUTUBE_URL,
            ]
            result = subprocess.run(cmd2, capture_output=True, text=True, timeout=120)

        if os.path.exists(AUDIO_FILE):
            print(f"[Audio] Download complete!")
            return True
        else:
            # Check for the file with different extension
            base = AUDIO_FILE.replace(".wav", "")
            for ext in [".wav", ".webm", ".m4a", ".mp3", ".ogg"]:
                if os.path.exists(base + ext):
                    os.rename(base + ext, AUDIO_FILE)
                    print(f"[Audio] Download complete (converted from {ext})")
                    return True
            print(f"[Audio] Download failed. stderr: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"[Audio] Download error: {e}")
        return False


def analyze_audio_file():
    """Pre-analyze the audio file to extract frequency bands over time."""
    import librosa

    print("[Audio] Analyzing audio frequencies...")
    y, sr = librosa.load(AUDIO_FILE, sr=22050, mono=True)
    duration = len(y) / sr
    print(f"[Audio] Duration: {duration:.1f}s, Sample Rate: {sr}Hz")

    # Compute Short-Time Fourier Transform
    hop_length = 512
    n_fft = 2048

    # Mel spectrogram for perceptual frequency bands
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=n_fft,
                                       hop_length=hop_length, n_mels=32)
    S_db = librosa.power_to_db(S, ref=np.max)
    # Normalize to 0-1
    S_norm = (S_db - S_db.min()) / (S_db.max() - S_db.min() + 1e-8)

    # Extract specific frequency bands that matter for a fly:
    # - Sub-bass (20-60Hz) → vibration/mechanosensory
    # - Bass (60-250Hz) → wing-beat frequency range (~200Hz for flies!)
    # - Low-mid (250-500Hz) → courtship song detection
    # - Mid (500-2000Hz) → general hearing range
    # - High (2000-8000Hz) → predator detection range
    # - Ultra-high (8000+Hz) → stress-inducing

    # Get full STFT for band extraction
    D = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop_length))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    def band_energy(f_low, f_high):
        mask = (freqs >= f_low) & (freqs < f_high)
        if not np.any(mask):
            return np.zeros(D.shape[1])
        energy = np.mean(D[mask, :], axis=0)
        e_max = np.max(energy) + 1e-8
        return energy / e_max

    bands = {
        "sub_bass": band_energy(20, 60),
        "bass": band_energy(60, 250),
        "low_mid": band_energy(250, 500),
        "mid": band_energy(500, 2000),
        "high": band_energy(2000, 8000),
        "ultra_high": band_energy(8000, 11025),
    }

    # Beat detection for rhythm-synchronized neural responses
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr,
                                                  hop_length=hop_length)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr,
                                         hop_length=hop_length)

    # RMS energy (overall loudness over time)
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    rms_norm = rms / (np.max(rms) + 1e-8)

    # Spectral centroid (brightness/sharpness)
    cent = librosa.feature.spectral_centroid(y=y, sr=sr,
                                              hop_length=hop_length)[0]
    cent_norm = cent / (np.max(cent) + 1e-8)

    # Onset strength (sudden changes = startling)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr,
                                              hop_length=hop_length)
    onset_norm = onset_env / (np.max(onset_env) + 1e-8)

    # Handle tempo being an array (newer librosa returns array)
    tempo_val = float(tempo) if np.isscalar(tempo) else float(tempo[0])

    print(f"[Audio] Tempo: {tempo_val:.1f} BPM")
    print(f"[Audio] {len(beat_times)} beats detected")
    print(f"[Audio] {D.shape[1]} time frames extracted")

    return {
        "bands": bands,
        "mel_spectrogram": S_norm,
        "rms": rms_norm,
        "centroid": cent_norm,
        "onset": onset_norm,
        "beat_times": beat_times,
        "tempo": tempo_val,
        "duration": duration,
        "sr": sr,
        "hop_length": hop_length,
        "num_frames": D.shape[1],
    }


# ── HTTP DATA SERVER ──────────────────────────────────
# Serves real-time brain data to the HTML dashboard via polling.
# Dashboard fetches /api/brain every ~100ms for live updates.

import http.server
import socketserver

# Global state: latest brain data for the dashboard to poll
_latest_brain_data = {}
_data_lock = threading.Lock()
dashboard_port = 9876


def update_dashboard_data(data_dict):
    """Store latest brain data for dashboard polling."""
    global _latest_brain_data
    with _data_lock:
        _latest_brain_data = data_dict


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    """Serves dashboard HTML and brain data API."""

    def do_GET(self):
        if self.path == "/api/brain":
            self._serve_brain_data()
        elif self.path == "/" or self.path == "/dashboard":
            self._serve_dashboard()
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_dashboard(self):
        """Serve the dashboard HTML file."""
        dashboard_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))),
            "music_brain_dashboard.html"
        )
        if os.path.exists(dashboard_path):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            with open(dashboard_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(f"Dashboard not found at: {dashboard_path}".encode())

    def _serve_brain_data(self):
        """Serve latest brain state as JSON."""
        with _data_lock:
            data = _latest_brain_data.copy()

        try:
            payload = json.dumps(data, default=str).encode("utf-8")
        except Exception:
            payload = b"{}"

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass  # Suppress HTTP logs


class ThreadedHTTPServer(socketserver.ThreadingTCPServer):
    """Threaded HTTP server for concurrent dashboard requests."""
    allow_reuse_address = True
    daemon_threads = True


def start_dashboard_server():
    """Start the dashboard HTTP server in a background thread."""
    server = ThreadedHTTPServer(("", dashboard_port), DashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[Server] Dashboard running at http://localhost:{dashboard_port}")
    return server


# ── FLY BRAIN SETUP ───────────────────────────────────
from flybrain import FlyBrain, FeatureDetectors

print("\n[Brain] Loading connectome for music experiment...")
brain = FlyBrain(device="cpu")
fd = FeatureDetectors(brain)
dns = brain.cells(["descending_neuron"])
num_dns = len(dns)
print(f"[Brain] {num_dns} descending neurons loaded")

# Dopamine neurons
dans = brain.cells(["DAN"])
if len(dans) == 0:
    dans = dns[:50]
print(f"[Brain] {len(dans)} dopamine neurons")

# ── AUDITORY NEURONS ──
# Real fly auditory pathway: Johnston's Organ → AMMC → IVLP → WED
# Johnston's organ neurons detect sound vibrations (antennal hearing)

# Try to get actual auditory-related cell types
auditory_neurons = brain.cells(["JON", "AMMC", "WED"])  # Johnston's Organ Neurons
if len(auditory_neurons) < 64:
    # Fallback: use Kenyon Cells (mushroom body — involved in learning)
    auditory_neurons = brain.cells(["KenyonCell"])
    if len(auditory_neurons) < 64:
        auditory_neurons = dns[:200]

print(f"[Brain] {len(auditory_neurons)} auditory/mechanosensory neurons available")

# Partition auditory neurons into frequency-sensitive groups
# (In real flies, different JO neurons respond to different frequencies)
n_aud = len(auditory_neurons)
sub_bass_neurons = auditory_neurons[:n_aud // 6]
bass_neurons = auditory_neurons[n_aud // 6: 2 * n_aud // 6]
low_mid_neurons = auditory_neurons[2 * n_aud // 6: 3 * n_aud // 6]
mid_neurons = auditory_neurons[3 * n_aud // 6: 4 * n_aud // 6]
high_neurons = auditory_neurons[4 * n_aud // 6: 5 * n_aud // 6]
ultra_high_neurons = auditory_neurons[5 * n_aud // 6:]

FREQ_NEURON_MAP = {
    "sub_bass": sub_bass_neurons,
    "bass": bass_neurons,
    "low_mid": low_mid_neurons,
    "mid": mid_neurons,
    "high": high_neurons,
    "ultra_high": ultra_high_neurons,
}

# Stress-related neurons (real fly stress response)
# Octopamine neurons (fly equivalent of norepinephrine — fight/flight)
stress_neurons = brain.cells(["OA"])  # Octopaminergic
if len(stress_neurons) < 20:
    stress_neurons = dns[270:320]
print(f"[Brain] {len(stress_neurons)} stress/octopamine neurons")

# Motor command populations (descending neurons → muscles)
# We'll track these to see if the fly tries to "escape" the sound
escape_pop = dns[170:200]   # dash/escape neurons
freeze_pop = dns[190:210]   # block/freeze neurons
wing_pop = dns[0:50]        # forward movement (wing-related)

# ── POPULATION GROUPS (same as rl.py for consistency) ──
POPULATIONS = {
    "escape": dns[170:200],
    "freeze": dns[190:210],
    "wings": dns[0:80],
    "aggression": dns[80:110],
    "avoidance": dns[45:80],
    "approach": dns[0:45],
}

# ── NEURAL HEALTH TRACKING ───────────────────────────
class NeuralHealthTracker:
    """
    Tracks signs of neural 'damage' from excessive stimulation.

    In real neuroscience, overstimulation causes:
    - Excitotoxicity (neurons fire too much and die)
    - Calcium overload
    - Synaptic fatigue (can't fire anymore)
    - Spreading depression (waves of silencing)

    We simulate these effects by tracking:
    - Sustained high firing rates → excitotoxicity risk
    - Neurons that stop responding → fatigue/death
    - Overall brain coherence → healthy brains have structured patterns
    """

    def __init__(self, num_neurons):
        self.num_neurons = num_neurons
        self.fire_counts = np.zeros(num_neurons, dtype=np.float32)
        self.fatigue = np.zeros(num_neurons, dtype=np.float32)
        self.dead_neurons = np.zeros(num_neurons, dtype=bool)
        self.coherence_history = deque(maxlen=100)
        self.stress_level = 0.0
        self.damage_events = []
        self.total_damage = 0.0

        # Phase tracking
        self.phase = "BASELINE"  # BASELINE → STIMULATED → STRESSED → DAMAGED → CRITICAL
        self.phase_history = deque(maxlen=500)

        # Meme triggers
        self.current_meme = "neutral"
        self.meme_history = deque(maxlen=50)
        self.meme_cooldown = 0

        # Time tracking
        self.step_count = 0
        self.phase_start_step = 0

    def update(self, brain_state, arousal, dopamine, fired_count):
        """Update health metrics after each brain step."""
        self.step_count += 1

        # Count firing
        fired_mask = brain_state.astype(np.float32)
        self.fire_counts += fired_mask

        # Fatigue: neurons that fire too much get tired
        # (exponential accumulation with slow recovery)
        self.fatigue += fired_mask * 0.02
        self.fatigue *= 0.995  # Slow recovery
        self.fatigue = np.clip(self.fatigue, 0, 1.0)

        # Excitotoxicity: sustained firing above threshold kills neurons
        overtaxed = self.fatigue > 0.85
        newly_dead = overtaxed & ~self.dead_neurons
        if np.any(newly_dead):
            self.dead_neurons |= newly_dead
            dead_count = int(np.sum(newly_dead))
            self.damage_events.append({
                "step": self.step_count,
                "type": "EXCITOTOXICITY",
                "neurons_lost": dead_count,
                "total_dead": int(np.sum(self.dead_neurons)),
            })
            self.total_damage += dead_count * 0.1
            print(f"[DAMAGE] ⚡ {dead_count} neurons died from overstimulation! "
                  f"(Total dead: {int(np.sum(self.dead_neurons))})")

        # Brain coherence: measure how structured the firing pattern is
        # (random firing = low coherence = brain damage indicator)
        firing_rate = fired_count / self.num_neurons
        expected_rate = 0.15  # Healthy baseline
        coherence = 1.0 - abs(firing_rate - expected_rate) / max(expected_rate, 0.01)
        coherence = max(0.0, min(1.0, coherence))
        self.coherence_history.append(coherence)

        # Stress level
        high_firing = firing_rate > 0.3
        very_high_firing = firing_rate > 0.5
        fatigue_avg = float(np.mean(self.fatigue))

        if very_high_firing:
            self.stress_level += 0.05
        elif high_firing:
            self.stress_level += 0.02
        else:
            self.stress_level -= 0.01

        self.stress_level += fatigue_avg * 0.01
        self.stress_level = np.clip(self.stress_level, 0.0, 1.0)

        # Phase determination
        dead_pct = float(np.sum(self.dead_neurons)) / self.num_neurons
        old_phase = self.phase

        if dead_pct > 0.25:
            self.phase = "CRITICAL"
        elif dead_pct > 0.10:
            self.phase = "DAMAGED"
        elif self.stress_level > 0.6:
            self.phase = "STRESSED"
        elif self.stress_level > 0.2:
            self.phase = "STIMULATED"
        else:
            self.phase = "BASELINE"

        if self.phase != old_phase:
            self.phase_start_step = self.step_count
            print(f"[Phase] Brain state: {old_phase} → {self.phase}")

        self.phase_history.append(self.phase)

        # Meme selection based on brain state
        self.meme_cooldown = max(0, self.meme_cooldown - 1)
        if self.meme_cooldown == 0:
            self._select_meme(firing_rate, arousal, dopamine, dead_pct)

        return {
            "dead_count": int(np.sum(self.dead_neurons)),
            "dead_pct": dead_pct,
            "avg_fatigue": fatigue_avg,
            "stress_level": float(self.stress_level),
            "coherence": float(np.mean(list(self.coherence_history))) if self.coherence_history else 1.0,
            "phase": self.phase,
            "total_damage": self.total_damage,
            "meme": self.current_meme,
            "firing_rate": firing_rate,
        }

    def _select_meme(self, firing_rate, arousal, dopamine, dead_pct):
        """Select a meme reaction based on the fly's current state."""
        # Each meme has conditions and a cooldown
        new_meme = self.current_meme

        if dead_pct > 0.25:
            new_meme = "skull"  # 💀 brain is cooked
        elif dead_pct > 0.15:
            new_meme = "explosion"  # 🤯 brain melting
        elif dead_pct > 0.05:
            new_meme = "crying"  # 😭 neurons dying
        elif self.stress_level > 0.8:
            new_meme = "screaming"  # 😱 extreme stress
        elif self.stress_level > 0.6:
            new_meme = "sweating"  # 😰 stressed
        elif self.stress_level > 0.4:
            new_meme = "dizzy"  # 😵‍💫 getting overwhelmed
        elif firing_rate > 0.5:
            new_meme = "fire"  # 🔥 brain lit up
        elif firing_rate > 0.3:
            new_meme = "shocked"  # 😲 lots of activity
        elif arousal > 0.7:
            new_meme = "hype"  # 🤩 vibing hard
        elif dopamine > 0.5:
            new_meme = "vibing"  # 😎 enjoying it
        elif dopamine < -0.5:
            new_meme = "pain"  # 😫 not enjoying
        elif firing_rate < 0.05:
            new_meme = "sleeping"  # 😴 barely responding
        else:
            new_meme = "thinking"  # 🤔 processing

        if new_meme != self.current_meme:
            self.current_meme = new_meme
            self.meme_cooldown = 40  # Don't change for ~2 seconds
            self.meme_history.append((self.step_count, new_meme))

    def get_fatigue_map(self):
        """Return the fatigue heatmap for visualization."""
        return self.fatigue.copy()

    def get_dead_map(self):
        """Return which neurons are dead."""
        return self.dead_neurons.copy()


# ── MAIN EXPERIMENT LOOP ──────────────────────────────
def run_music_experiment():
    """Main experiment: play AIZO to the fly brain and observe."""
    import webbrowser

    print("\n" + "=" * 60)
    print("  EXPERIMENT: FLY BRAIN × AIZO MUSIC")
    print("=" * 60)

    # Step 1: Download audio
    print("\n[Step 1] Downloading audio...")
    if not download_audio():
        print("[ERROR] Could not download audio. Creating synthetic test audio.")
        _create_synthetic_audio()

    # Step 2: Analyze audio
    print("\n[Step 2] Analyzing audio frequencies...")
    audio_data = analyze_audio_file()

    # Step 3: Start WebSocket server for dashboard
    print("\n[Step 3] Starting brain dashboard server...")
    server = start_dashboard_server()

    # Step 4: Open dashboard in browser
    dashboard_url = f"http://localhost:{dashboard_port}"
    print(f"\n[Step 4] Opening brain dashboard at {dashboard_url}")
    webbrowser.open(dashboard_url)

    # Step 5: Start audio playback
    print("\n[Step 5] Initializing audio playback...")
    try:
        import pygame
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=1024)
        pygame.mixer.music.load(AUDIO_FILE)
    except Exception as e:
        print(f"[Audio] Pygame init error: {e}")
        print("[Audio] Will run experiment without audio playback (data only)")
        pygame = None

    # Initialize tracking
    health_tracker = NeuralHealthTracker(num_dns)
    arousal = 0.0
    dopamine = 0.0
    brain_memory = deque(maxlen=10)

    # Experiment data log
    experiment_log = {
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "music": "AIZO",
        "youtube_url": YOUTUBE_URL,
        "tempo": audio_data["tempo"],
        "duration": audio_data["duration"],
        "num_neurons": num_dns,
        "frames": [],
    }

    print("\n" + "=" * 60)
    print("  STARTING EXPERIMENT IN 3 SECONDS")
    print("  The dashboard should open in your browser.")
    print("  Press Ctrl+C to stop the experiment.")
    print("=" * 60)
    time.sleep(3)

    # Start music
    if pygame:
        try:
            pygame.mixer.music.play()
            music_playing = True
            print("[Audio] ♪ Music started playing!")
        except Exception as e:
            print(f"[Audio] Playback error: {e}")
            music_playing = False
    else:
        music_playing = False

    playback_start = time.time()
    step = 0
    frames_per_second = 20  # Target FPS for brain simulation
    frame_interval = 1.0 / frames_per_second

    try:
        while True:
            loop_start = time.time()
            elapsed_time = time.time() - playback_start

            # Stop if we've exceeded the audio duration
            if elapsed_time > audio_data["duration"] + 5:
                print("\n[Experiment] Audio ended. Running 5s cool-down...")
                # Run a cool-down period to see recovery
                for cooldown_step in range(100):
                    # No audio input during cooldown
                    injections = []
                    for dn in dns[:20]:
                        injections.append((dn, 0.01))  # Minimal baseline

                    fired_neurons = brain.step(inject=injections)
                    fired_set = set(fired_neurons)
                    brain_state = np.array(
                        [1 if dn in fired_set else 0 for dn in dns],
                        dtype=np.uint8
                    )

                    health = health_tracker.update(
                        brain_state, arousal, dopamine, len(fired_set)
                    )
                    dopamine *= 0.95
                    arousal *= 0.95

                    # Send to dashboard
                    update_dashboard_data({
                        "type": "brain_update",
                        "step": step + cooldown_step,
                        "phase": "COOLDOWN",
                        "elapsed": elapsed_time + cooldown_step * 0.05,
                        "fired_count": len(fired_set),
                        "total_neurons": num_dns,
                        "brain_state": brain_state[:500].tolist(),
                        "health": health,
                        "arousal": float(arousal),
                        "dopamine": float(dopamine),
                        "audio": {"sub_bass": 0, "bass": 0, "low_mid": 0,
                                  "mid": 0, "high": 0, "ultra_high": 0,
                                  "rms": 0, "onset": 0, "is_beat": False},
                        "populations": {},
                        "meme": health["meme"],
                        "fatigue_map": health_tracker.get_fatigue_map()[:200].tolist(),
                        "dead_map": health_tracker.get_dead_map()[:200].tolist(),
                    })
                    time.sleep(0.05)

                break  # End experiment

            # ── GET CURRENT AUDIO FRAME ──
            frame_idx = int(elapsed_time * audio_data["sr"] / audio_data["hop_length"])
            frame_idx = min(frame_idx, audio_data["num_frames"] - 1)

            # Extract current frequency band energies
            current_audio = {}
            for band_name, band_data in audio_data["bands"].items():
                current_audio[band_name] = float(band_data[frame_idx])

            current_audio["rms"] = float(audio_data["rms"][min(frame_idx, len(audio_data["rms"]) - 1)])
            current_audio["onset"] = float(audio_data["onset"][min(frame_idx, len(audio_data["onset"]) - 1)])
            current_audio["centroid"] = float(audio_data["centroid"][min(frame_idx, len(audio_data["centroid"]) - 1)])

            # Check if we're on a beat
            is_beat = any(abs(elapsed_time - bt) < 0.05 for bt in audio_data["beat_times"])
            current_audio["is_beat"] = is_beat

            # ── INJECT AUDIO INTO FLY BRAIN ──
            injections = []

            # Map frequency bands to auditory neuron populations
            for band_name, neurons in FREQ_NEURON_MAP.items():
                energy = current_audio.get(band_name, 0.0)
                # Scale injection by energy level
                # Bass frequencies are especially strong for flies
                # (their antennae resonate near 200-400Hz)
                scale = 1.0
                if band_name in ("bass", "low_mid"):
                    scale = 2.5  # Flies are most sensitive here
                elif band_name == "sub_bass":
                    scale = 1.8  # Feel the vibrations
                elif band_name in ("high", "ultra_high"):
                    scale = 1.5  # Startling high frequencies

                injection_strength = energy * scale * current_audio["rms"]

                for neuron in neurons:
                    injections.append((neuron, injection_strength))

            # Beat synchronization → dopamine pulse
            if is_beat:
                beat_strength = current_audio["rms"] * 2.0
                for dan in dans[:min(30, len(dans))]:
                    injections.append((dan, beat_strength))

            # Onset (sudden changes) → startle response
            if current_audio["onset"] > 0.5:
                startle = current_audio["onset"] * 1.5
                for sn in stress_neurons[:min(15, len(stress_neurons))]:
                    injections.append((sn, startle))

            # Loud sections → general arousal boost
            if current_audio["rms"] > 0.7:
                for dn in dns[:30]:
                    injections.append((dn, current_audio["rms"] * 0.5))

            # ── SIMULATE BRAIN STEP ──
            fired_neurons = brain.step(inject=injections)
            fired_set = set(fired_neurons)

            brain_state = np.array(
                [1 if dn in fired_set else 0 for dn in dns],
                dtype=np.uint8
            )

            # ── UPDATE AROUSAL & DOPAMINE ──
            firing_rate = len(fired_set) / num_dns
            brain_memory.append(firing_rate)

            # Arousal from sustained stimulation
            arousal = arousal * 0.93 + firing_rate * 0.2
            arousal = min(arousal, 1.0)

            # Dopamine from beat alignment and novel patterns
            if is_beat and firing_rate > 0.2:
                dopamine += 0.1  # Rhythm feels good
            if current_audio["onset"] > 0.7:
                dopamine -= 0.05  # Sudden changes are aversive
            dopamine = dopamine * 0.97  # Decay
            dopamine = np.clip(dopamine, -2.0, 2.0)

            # ── TRACK NEURAL HEALTH ──
            health = health_tracker.update(
                brain_state, arousal, dopamine, len(fired_set)
            )

            # ── POPULATION FIRING RATES ──
            pop_data = {}
            for pop_name, pop_neurons in POPULATIONS.items():
                rate = sum(1 for n in pop_neurons if n in fired_set) / len(pop_neurons)
                pop_data[pop_name] = float(rate)

            # ── SEND TO DASHBOARD ──
            if step % 2 == 0:  # Update every other frame
                update_dashboard_data({
                    "type": "brain_update",
                    "step": step,
                    "phase": health["phase"],
                    "elapsed": elapsed_time,
                    "duration": audio_data["duration"],
                    "tempo": audio_data["tempo"],
                    "fired_count": len(fired_set),
                    "total_neurons": num_dns,
                    "brain_state": brain_state[:500].tolist(),
                    "health": health,
                    "arousal": float(arousal),
                    "dopamine": float(dopamine),
                    "audio": current_audio,
                    "populations": pop_data,
                    "meme": health["meme"],
                    "fatigue_map": health_tracker.get_fatigue_map()[:200].tolist(),
                    "dead_map": health_tracker.get_dead_map()[:200].tolist(),
                })

            # ── CONSOLE OUTPUT ──
            if step % 40 == 0:  # Every ~2 seconds
                print(f"[{elapsed_time:6.1f}s] "
                      f"Phase={health['phase']:10s} "
                      f"Fired={len(fired_set):4d}/{num_dns} "
                      f"Dead={health['dead_count']:3d} "
                      f"Stress={health['stress_level']:.2f} "
                      f"Meme={health['meme']}")

            # Log frame
            if step % 10 == 0:
                experiment_log["frames"].append({
                    "step": step,
                    "time": elapsed_time,
                    "fired": len(fired_set),
                    "phase": health["phase"],
                    "stress": health["stress_level"],
                    "dead": health["dead_count"],
                    "dopamine": float(dopamine),
                    "arousal": float(arousal),
                    "meme": health["meme"],
                })

            # ── FRAME TIMING ──
            elapsed_frame = time.time() - loop_start
            if elapsed_frame < frame_interval:
                time.sleep(frame_interval - elapsed_frame)

            step += 1

    except KeyboardInterrupt:
        print("\n\n[Experiment] Stopped by user.")

    # ── SAVE RESULTS ──
    if pygame and music_playing:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    experiment_log["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    experiment_log["total_steps"] = step
    experiment_log["final_health"] = {
        "dead_neurons": int(np.sum(health_tracker.dead_neurons)),
        "dead_pct": float(np.sum(health_tracker.dead_neurons)) / num_dns,
        "total_damage": health_tracker.total_damage,
        "final_phase": health_tracker.phase,
        "final_stress": float(health_tracker.stress_level),
        "damage_events": health_tracker.damage_events,
    }

    log_path = os.path.join(DATA_DIR, f"music_experiment_{int(time.time())}.json")
    with open(log_path, "w") as f:
        json.dump(experiment_log, f, indent=2, default=str)
    print(f"\n[Experiment] Results saved to {log_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("  EXPERIMENT RESULTS SUMMARY")
    print("=" * 60)
    fh = experiment_log["final_health"]
    print(f"  Total brain cycles:    {step}")
    print(f"  Neurons killed:        {fh['dead_neurons']}/{num_dns} "
          f"({fh['dead_pct']*100:.1f}%)")
    print(f"  Total damage score:    {fh['total_damage']:.2f}")
    print(f"  Final brain phase:     {fh['final_phase']}")
    print(f"  Final stress level:    {fh['final_stress']:.2f}")
    print(f"  Damage events:         {len(fh['damage_events'])}")
    print("=" * 60)

    if fh['dead_pct'] > 0.2:
        print("\n  ⚠️  VERDICT: SEVERE BRAIN DAMAGE")
        print("  The fly's brain was significantly damaged by AIZO.")
        print("  Over 20% of neurons died from excitotoxicity.")
    elif fh['dead_pct'] > 0.05:
        print("\n  ⚠️  VERDICT: MODERATE BRAIN DAMAGE")
        print("  Some neurons were lost, but the brain partially survived.")
    elif fh['dead_pct'] > 0.01:
        print("\n  🔶 VERDICT: MILD STRESS DAMAGE")
        print("  Minor neural casualties. The fly survived but is shaken.")
    else:
        print("\n  ✅ VERDICT: BRAIN SURVIVED")
        print("  The fly's brain handled the music without significant damage.")

    # Send final summary to dashboard
    update_dashboard_data({
        "type": "experiment_complete",
        "summary": experiment_log["final_health"],
        "verdict": fh['final_phase'],
        "total_steps": step,
    })

    input("\n  Press Enter to return to the menu...")


def _create_synthetic_audio():
    """Create a synthetic audio file for testing if download fails."""
    print("[Audio] Creating synthetic AIZO-like test audio...")
    sr = 22050
    duration = 30  # 30 seconds of synthetic bass
    t = np.linspace(0, duration, int(sr * duration))

    # Bass drops + kicks
    bass = np.sin(2 * np.pi * 50 * t) * 0.3  # Sub-bass
    kick = np.sin(2 * np.pi * 100 * t) * np.exp(-4 * (t % 0.5)) * 0.5
    hi_hat = np.random.randn(len(t)) * 0.05 * (np.sin(2 * np.pi * 4 * t) > 0.5)
    wobble = np.sin(2 * np.pi * (200 + 100 * np.sin(2 * np.pi * 2 * t)) * t) * 0.2

    audio = bass + kick + hi_hat + wobble
    audio = audio / np.max(np.abs(audio)) * 0.9

    import soundfile as sf
    try:
        sf.write(AUDIO_FILE, audio.astype(np.float32), sr)
        print(f"[Audio] Synthetic audio saved to {AUDIO_FILE}")
    except ImportError:
        # Fallback: save as raw WAV manually
        import wave
        audio_int16 = (audio * 32767).astype(np.int16)
        with wave.open(AUDIO_FILE, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(audio_int16.tobytes())
        print(f"[Audio] Synthetic audio saved to {AUDIO_FILE}")


if __name__ == "__main__":
    run_music_experiment()
