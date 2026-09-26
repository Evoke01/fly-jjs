import time
import os
import sys
import json
import socket
import threading
import subprocess
import numpy as np
from collections import deque
import http.server
import socketserver

YOUTUBE_URL = "https://youtu.be/zz2a9Q2Wru0?si=8yQpc-Fdlc3me4s8"
AUDIO_DIR = os.path.expanduser("~/.fly_jjs/audio")
os.makedirs(AUDIO_DIR, exist_ok=True)
AUDIO_FILE = os.path.join(AUDIO_DIR, "aizo_experiment.wav")

DATA_DIR = os.path.expanduser("~/.fly_jjs/experiment_data")
os.makedirs(DATA_DIR, exist_ok=True)

_latest_brain_data = {}
_data_lock = threading.Lock()
dashboard_port = 9876


def update_dashboard_data(data_dict):
    global _latest_brain_data
    with _data_lock:
        _latest_brain_data = data_dict


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/brain":
            self._serve_brain_data()
        elif self.path == "/" or self.path == "/dashboard":
            self._serve_dashboard()
        elif self.path.startswith("/memes/"):
            self._serve_meme()
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_dashboard(self):
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

    def _serve_meme(self):
        filename = os.path.basename(self.path)
        meme_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))),
            "memes"
        )
        meme_path = os.path.join(meme_dir, filename)
        
        if os.path.exists(meme_path) and os.path.isfile(meme_path):
            self.send_response(200)
            if filename.endswith(".png"):
                self.send_header("Content-Type", "image/png")
            elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
                self.send_header("Content-Type", "image/jpeg")
            elif filename.endswith(".gif"):
                self.send_header("Content-Type", "image/gif")
            self.send_header("Cache-Control", "public, max-age=31536000")
            self.end_headers()
            with open(meme_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Meme not found")

    def _serve_brain_data(self):
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
        pass


class ThreadedHTTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_dashboard_server():
    server = ThreadedHTTPServer(("", dashboard_port), DashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[Server] Dashboard running at http://localhost:{dashboard_port}")
    return server


def download_audio(target_url=YOUTUBE_URL, target_file=AUDIO_FILE):
    if os.path.exists(target_file):
        print(f"[Audio] Found cached audio: {target_file}")
        return True

    print(f"[Audio] Downloading from YouTube...")
    print(f"[Audio] URL: {target_url}")

    try:
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "-x",
            "--audio-format", "wav",
            "--audio-quality", "0",
            "-o", target_file.replace(".wav", ".%(ext)s"),
            "--no-playlist",
            target_url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            cmd2 = [
                "yt-dlp",
                "-x", "--audio-format", "wav",
                "-o", target_file.replace(".wav", ".%(ext)s"),
                "--no-playlist",
                target_url,
            ]
            result = subprocess.run(cmd2, capture_output=True, text=True, timeout=120)

        if os.path.exists(target_file):
            print(f"[Audio] Download complete!")
            return True
        else:
            base = target_file.replace(".wav", "")
            for ext in [".wav", ".webm", ".m4a", ".mp3", ".ogg"]:
                if os.path.exists(base + ext):
                    os.rename(base + ext, target_file)
                    print(f"[Audio] Download complete (converted from {ext})")
                    return True
            print(f"[Audio] Download failed.")
            return False
    except Exception as e:
        print(f"[Audio] Download error: {e}")
        return False


def _create_synthetic_audio(target_file=AUDIO_FILE):
    print("[Audio] Creating synthetic AIZO-like test audio...")
    sr = 22050
    duration = 30
    t = np.linspace(0, duration, int(sr * duration))

    bass = np.sin(2 * np.pi * 50 * t) * 0.3
    kick = np.sin(2 * np.pi * 100 * t) * np.exp(-4 * (t % 0.5)) * 0.5
    hi_hat = np.random.randn(len(t)) * 0.05 * (np.sin(2 * np.pi * 4 * t) > 0.5)
    wobble = np.sin(2 * np.pi * (200 + 100 * np.sin(2 * np.pi * 2 * t)) * t) * 0.2

    audio = bass + kick + hi_hat + wobble
    audio = audio / np.max(np.abs(audio)) * 0.9

    import wave
    audio_int16 = (audio * 32767).astype(np.int16)
    with wave.open(target_file, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_int16.tobytes())
    print(f"[Audio] Synthetic audio saved to {target_file}")


def analyze_audio_file(target_file=AUDIO_FILE):
    import librosa

    print("[Audio] Analyzing audio frequencies...")
    y, sr = librosa.load(target_file, sr=22050, mono=True)
    duration = len(y) / sr

    hop_length = 512
    n_fft = 2048

    S = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=n_fft, hop_length=hop_length, n_mels=32)
    S_db = librosa.power_to_db(S, ref=np.max)
    S_norm = (S_db - S_db.min()) / (S_db.max() - S_db.min() + 1e-8)

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

    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop_length)

    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    rms_norm = rms / (np.max(rms) + 1e-8)

    cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    cent_norm = cent / (np.max(cent) + 1e-8)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    onset_norm = onset_env / (np.max(onset_env) + 1e-8)

    tempo_val = float(tempo) if np.isscalar(tempo) else float(tempo[0])

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


class NeuralHealthTracker:
    def __init__(self, num_neurons):
        self.num_neurons = num_neurons
        self.fire_counts = np.zeros(num_neurons, dtype=np.float32)
        self.fatigue = np.zeros(num_neurons, dtype=np.float32)
        self.dead_neurons = np.zeros(num_neurons, dtype=bool)
        self.coherence_history = deque(maxlen=100)
        self.stress_level = 0.0
        self.damage_events = []
        self.total_damage = 0.0

        self.phase = "BASELINE"
        self.phase_history = deque(maxlen=500)

        self.current_meme = "neutral"
        self.meme_history = deque(maxlen=50)
        self.meme_cooldown = 0
        self.step_count = 0

    def update(self, brain_state, arousal, dopamine, fired_count):
        self.step_count += 1
        fired_mask = brain_state.astype(np.float32)
        self.fire_counts += fired_mask

        self.fatigue += fired_mask * 0.02
        self.fatigue *= 0.995
        self.fatigue = np.clip(self.fatigue, 0, 1.0)

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

        firing_rate = fired_count / self.num_neurons
        expected_rate = 0.15
        coherence = max(0.0, min(1.0, 1.0 - abs(firing_rate - expected_rate) / max(expected_rate, 0.01)))
        self.coherence_history.append(coherence)

        if firing_rate > 0.5:
            self.stress_level += 0.05
        elif firing_rate > 0.3:
            self.stress_level += 0.02
        else:
            self.stress_level -= 0.01

        fatigue_avg = float(np.mean(self.fatigue))
        self.stress_level += fatigue_avg * 0.01
        self.stress_level = float(np.clip(self.stress_level, 0.0, 1.0))

        dead_pct = float(np.sum(self.dead_neurons)) / self.num_neurons
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
        new_meme = self.current_meme
        if dead_pct > 0.25:
            new_meme = "skull"
        elif dead_pct > 0.15:
            new_meme = "explosion"
        elif dead_pct > 0.05:
            new_meme = "crying"
        elif self.stress_level > 0.8:
            new_meme = "screaming"
        elif self.stress_level > 0.6:
            new_meme = "sweating"
        elif self.stress_level > 0.4:
            new_meme = "dizzy"
        elif firing_rate > 0.5:
            new_meme = "fire"
        elif firing_rate > 0.3:
            new_meme = "shocked"
        elif arousal > 0.7:
            new_meme = "hype"
        elif dopamine > 0.5:
            new_meme = "vibing"
        elif dopamine < -0.5:
            new_meme = "pain"
        elif firing_rate < 0.05:
            new_meme = "sleeping"
        else:
            new_meme = "thinking"

        if new_meme != self.current_meme:
            self.current_meme = new_meme
            self.meme_cooldown = 40

    def get_fatigue_map(self):
        return self.fatigue.copy()

    def get_dead_map(self):
        return self.dead_neurons.copy()


def run_music_experiment(custom_url=None):
    import webbrowser
    import hashlib
    from flybrain import FlyBrain, FeatureDetectors

    url_to_use = custom_url if custom_url else YOUTUBE_URL
    url_hash = hashlib.md5(url_to_use.encode()).hexdigest()[:8]
    audio_file_path = os.path.join(AUDIO_DIR, f"experiment_{url_hash}.wav")

    print("=" * 60)
    print("  FLY BRAIN × MUSIC EXPERIMENT")
    print("=" * 60)

    print("\n[Step 1] Loading connectome...")
    brain = FlyBrain(device="cpu")
    fd = FeatureDetectors(brain)
    dns = brain.cells(["descending_neuron"])
    num_dns = len(dns)

    dans = brain.cells(["DAN"])
    if len(dans) == 0:
        dans = dns[:50]

    auditory_neurons = brain.cells(["JON", "AMMC", "WED"])
    if len(auditory_neurons) < 64:
        auditory_neurons = brain.cells(["KenyonCell"])
        if len(auditory_neurons) < 64:
            auditory_neurons = dns[:200]

    n_aud = len(auditory_neurons)
    freq_neuron_map = {
        "sub_bass": auditory_neurons[:n_aud // 6],
        "bass": auditory_neurons[n_aud // 6: 2 * n_aud // 6],
        "low_mid": auditory_neurons[2 * n_aud // 6: 3 * n_aud // 6],
        "mid": auditory_neurons[3 * n_aud // 6: 4 * n_aud // 6],
        "high": auditory_neurons[4 * n_aud // 6: 5 * n_aud // 6],
        "ultra_high": auditory_neurons[5 * n_aud // 6:],
    }

    stress_neurons = brain.cells(["OA"])
    if len(stress_neurons) < 20:
        stress_neurons = dns[270:320]

    populations = {
        "escape": dns[170:200],
        "freeze": dns[190:210],
        "wings": dns[0:80],
        "aggression": dns[80:110],
        "avoidance": dns[45:80],
        "approach": dns[0:45],
    }

    print("\n[Step 2] Preparing audio...")
    if not download_audio(url_to_use, audio_file_path):
        _create_synthetic_audio(audio_file_path)

    audio_data = analyze_audio_file(audio_file_path)

    print("\n[Step 3] Starting brain dashboard server...")
    server = start_dashboard_server()

    dashboard_url = f"http://localhost:{dashboard_port}"
    print(f"[Step 4] Opening brain dashboard at {dashboard_url}")
    try:
        webbrowser.open(dashboard_url)
    except Exception:
        pass

    try:
        import pygame
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=1024)
        pygame.mixer.music.load(audio_file_path)
        pygame.mixer.music.play()
    except Exception as e:
        print(f"[Audio] Audio output notice: {e}")

    health_tracker = NeuralHealthTracker(num_dns)
    arousal = 0.0
    dopamine = 0.0

    print("\n" + "=" * 60)
    print("  EXPERIMENT STARTED")
    print("  View dashboard at http://localhost:9876")
    print("  Press Ctrl+C to finish")
    print("=" * 60)

    playback_start = time.time()
    step = 0
    try:
        while True:
            loop_start = time.time()
            elapsed_time = time.time() - playback_start

            if elapsed_time > audio_data["duration"] + 2:
                break

            frame_idx = int(elapsed_time * audio_data["sr"] / audio_data["hop_length"])
            frame_idx = min(frame_idx, audio_data["num_frames"] - 1)

            current_audio = {}
            for band_name, band_data in audio_data["bands"].items():
                current_audio[band_name] = float(band_data[frame_idx])

            current_audio["rms"] = float(audio_data["rms"][min(frame_idx, len(audio_data["rms"]) - 1)])
            current_audio["onset"] = float(audio_data["onset"][min(frame_idx, len(audio_data["onset"]) - 1)])
            is_beat = any(abs(elapsed_time - bt) < 0.05 for bt in audio_data["beat_times"])
            current_audio["is_beat"] = is_beat

            injections = []
            for band_name, neurons in freq_neuron_map.items():
                energy = current_audio.get(band_name, 0.0)
                scale = 2.5 if band_name in ("bass", "low_mid") else 1.5
                injection_strength = energy * scale * current_audio["rms"]
                for neuron in neurons:
                    injections.append((neuron, injection_strength))

            if is_beat:
                for dan in dans[:min(30, len(dans))]:
                    injections.append((dan, current_audio["rms"] * 2.0))

            fired_neurons = brain.step(inject=injections)
            fired_set = set(fired_neurons)
            brain_state = np.array([1 if dn in fired_set else 0 for dn in dns], dtype=np.uint8)

            firing_rate = len(fired_set) / num_dns
            arousal = min(arousal * 0.93 + firing_rate * 0.2, 1.0)
            if is_beat and firing_rate > 0.2:
                dopamine += 0.1
            dopamine = float(np.clip(dopamine * 0.97, -2.0, 2.0))

            health = health_tracker.update(brain_state, arousal, dopamine, len(fired_set))

            pop_data = {}
            for pop_name, pop_neurons in populations.items():
                rate = sum(1 for n in pop_neurons if n in fired_set) / len(pop_neurons)
                pop_data[pop_name] = float(rate)

            if step % 2 == 0:
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

            if step % 40 == 0:
                print(f"[{elapsed_time:6.1f}s] Phase={health['phase']:10s} Fired={len(fired_set):4d}/{num_dns} Stress={health['stress_level']:.2f}")

            elapsed_frame = time.time() - loop_start
            if elapsed_frame < 0.05:
                time.sleep(0.05 - elapsed_frame)
            step += 1
    except KeyboardInterrupt:
        print("\n[Experiment] Interrupted by user.")

    print("\n[Experiment] Completed successfully!")


if __name__ == "__main__":
    run_music_experiment()
