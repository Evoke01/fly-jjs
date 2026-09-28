"""Live brain telemetry.

A running Play / Manual / Train session publishes a small snapshot of what the fly's
brain is doing a few times per second (TelemetryPublisher). The [L] menu option reads
it from a second terminal and draws it live (run_telemetry), so watching costs almost
nothing: no second brain, no extra screen capture.
"""
import json
import os
import time

from fly_jjs.core.storage import TELEMETRY_PATH

STALE_AFTER = 3.0   # seconds without an update before a session counts as gone


class TelemetryPublisher:
    """Writes the latest snapshot to disk, at most once per `interval` seconds."""

    def __init__(self, mode, interval=0.2, path=TELEMETRY_PATH):
        self.mode = mode
        self.interval = interval
        self.path = path
        self.started = time.time()
        self._last = 0.0

    def publish(self, snapshot, force=False):
        now = time.time()
        if not force and now - self._last < self.interval:
            return False
        self._last = now
        data = dict(snapshot, mode=self.mode, time=now, session_seconds=now - self.started)
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(data, f)
            os.replace(tmp, self.path)   # atomic: readers never see half a file
            return True
        except (OSError, TypeError, ValueError):
            return False

    def close(self, snapshot=None):
        self.publish(dict(snapshot or {}, ended=True), force=True)


def read_snapshot(path=TELEMETRY_PATH, max_age=STALE_AFTER):
    """The latest snapshot, or None if there is none. Old ones are marked 'stale'."""
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    data["stale"] = data.get("ended", False) or time.time() - data.get("time", 0) > max_age
    return data


def _bar(value, width=20):
    filled = int(round(max(0.0, min(1.0, value)) * width))
    return "█" * filled + "░" * (width - filled)


def render(data):
    """A rich renderable for one snapshot (or the waiting screen)."""
    from rich import box
    from rich.console import Group
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table

    if not data or data.get("stale"):
        why = "The last session ended." if data and data.get("ended") else "No session is running."
        return Panel(
            f"[bold yellow]{why}[/bold yellow]\n\n"
            "Start [bold]Play (1)[/bold], [bold]Manual Reward (M)[/bold] or [bold]Train (2)[/bold] "
            "in another terminal with [cyan]python main.py[/cyan].\n"
            "This screen updates by itself as soon as the fly starts thinking.\n\n"
            "[dim]Press Ctrl+C to go back to the menu.[/dim]",
            title="[bold cyan]📡 LIVE BRAIN TELEMETRY[/bold cyan]", border_style="yellow")

    actions = Table(title="Motor output (per frame)", box=box.SIMPLE_HEAVY, expand=True)
    actions.add_column("Action", style="bold white")
    actions.add_column("Press odds", style="green")
    actions.add_column("", justify="right")
    actions.add_column("Innate", style="magenta")
    pressed = set(data.get("pressed", []))
    innate = data.get("innate", {})
    for name, p in data.get("actions", {}).items():
        mark = "[bold green]●[/]" if name in pressed else "[dim]·[/]"
        actions.add_row(name.upper(), f"{_bar(p, 16)} {p * 100:4.0f}%", mark,
                        f"{innate.get(name, 0.0) * 100:4.1f}%")

    dopamine = data.get("dopamine", 0.0)
    dcolor = "green" if dopamine >= 0 else "red"
    hits = data.get("hits", {})
    brain = Panel(
        f"[bold cyan]Mode:[/] {data.get('mode', '?').upper()}   [bold cyan]Step:[/] {data.get('step', 0)}   "
        f"[bold cyan]FPS:[/] {data.get('fps', 0):.1f}\n"
        f"[bold cyan]Session:[/] {data.get('session_seconds', 0) / 60:.1f} min\n\n"
        f"[bold green]Neurons read:[/] {data.get('readout_neurons', 0):,} "
        f"({data.get('readout_active_pct', 0):.1f}% active)\n"
        f"[bold green]Descending neurons active:[/] {data.get('dn_active_pct', 0):.1f}%\n"
        f"[bold green]Neurons fired this step:[/] {data.get('fired', 0):,}\n"
        f"[bold {dcolor}]Dopamine (surprise):[/] {dopamine:+.2f}\n"
        f"[bold yellow]Expected reward (critic):[/] {data.get('value', 0):+.2f}\n"
        f"[bold yellow]Reward now / avg:[/] {data.get('reward', 0):+.2f} / {data.get('avg_reward', 0):+.3f}\n"
        f"[bold magenta]Total reward:[/] {data.get('total_reward', 0):+.1f}\n"
        f"[bold magenta]Hits landed / taken / kills:[/] {hits.get('landed', 0)} / "
        f"{hits.get('taken', 0)} / {hits.get('kills', 0)}",
        title="[bold yellow]🧠 Neural dynamics[/bold yellow]", border_style="green")

    vision_lines = [f"[bold cyan]Grid:[/] {data.get('resolution', '?')}  "
                    f"[bold cyan]Eye neurons:[/] {data.get('eye_neurons', 0):,}"]
    for channel, drive in data.get("vision", {}).items():
        vision_lines.append(f"{channel:>6} {_bar(drive * 2, 14)} {drive:.2f}")
    opp = data.get("opponent") or {}
    if opp.get("size", 0) > 0:
        distance = opp.get("distance", 1.0)
        where = "close" if distance < 0.35 else "mid" if distance < 0.7 else "far"
        vision_lines.append(f"[bold]Opponent:[/] {where}, dx {opp.get('dx', 0):+d}px  "
                            f"attack {opp.get('attack', 0):.2f}  threat {opp.get('threat', 0):.2f}")
    else:
        vision_lines.append("[bold]Opponent:[/] [dim]not in view[/dim]")
    if data.get("pattern_burst"):
        vision_lines.append("[bold red]Pattern: incoming burst predicted![/bold red]")
    vision = Panel("\n".join(vision_lines), title="[bold yellow]👁 Vision[/bold yellow]", border_style="cyan")

    events = data.get("events") or []
    feed = Panel("\n".join(events[-6:]) if events else "[dim]no reward events yet[/dim]",
                 title="[bold yellow]⚡ Recent events[/bold yellow]", border_style="magenta")

    layout = Layout()
    layout.split_row(Layout(actions, ratio=3), Layout(Group(brain, vision, feed), ratio=2))
    return Panel(layout, title="[bold cyan]📡 LIVE BRAIN TELEMETRY[/bold cyan]  [dim]Ctrl+C to exit[/dim]",
                 border_style="cyan", height=34)


def _plain_line(data):
    if not data or data.get("stale"):
        return "Waiting for a Play/Train session (start one in another terminal)..."
    top = sorted(data.get("actions", {}).items(), key=lambda kv: -kv[1])[:3]
    top_str = ", ".join(f"{k} {v * 100:.0f}%" for k, v in top)
    return (f"[{data.get('mode', '?')}] step {data.get('step', 0)} | DN active {data.get('dn_active_pct', 0):.1f}% "
            f"| dopamine {data.get('dopamine', 0):+.2f} | reward avg {data.get('avg_reward', 0):+.3f} | top: {top_str}")


def run_telemetry(path=TELEMETRY_PATH, refresh_hz=10):
    """Show the live telemetry of a session running in another terminal."""
    try:
        from rich.console import Console
        from rich.live import Live
    except ImportError:
        print("\n[Telemetry] Install 'rich' for the full dashboard (pip install rich). Plain mode:\n")
        try:
            while True:
                print(_plain_line(read_snapshot(path)))
                time.sleep(1.0)
        except KeyboardInterrupt:
            pass
        return

    console = Console()
    console.clear()
    try:
        with Live(render(read_snapshot(path)), console=console, refresh_per_second=refresh_hz,
                  screen=False) as live:
            while True:
                time.sleep(1.0 / refresh_hz)
                live.update(render(read_snapshot(path)))
    except KeyboardInterrupt:
        pass
    console.print("\n[bold green][✓] Telemetry monitor stopped.[/bold green]")


if __name__ == "__main__":
    run_telemetry()
