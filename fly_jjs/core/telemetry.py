import time
import os
import sys
import numpy as np

def run_telemetry():
    """Lightweight CLI real-time connectome telemetry monitor (~10 FPS, low CPU/RAM)."""
    try:
        from rich.console import Console
        from rich.live import Live
        from rich.panel import Panel
        from rich.layout import Layout
        from rich.table import Table
        from rich.progress import BarColumn, Progress
        from rich import box

        console = Console()
        console.clear()

        from fly_jjs.core.rl import get_brain_components, FlyLearner, NUM_ACTIONS, ACTION_NAMES, WEIGHTS_PATH
        brain, fd, dns, dans, retina_r, retina_b, populations = get_brain_components()

        learner = FlyLearner(len(dns), NUM_ACTIONS)
        learner.load(WEIGHTS_PATH)

        step = 0
        console.print("[bold yellow]Starting Live Brain Telemetry Stream (Press Ctrl+C to stop)...[/bold yellow]\n")
        time.sleep(1)

        def generate_telemetry_table(step, dopamine, total_reward):
            table = Table(title="[bold cyan]📡 REALTIME CONNECTOME TELEMETRY[/bold cyan]", box=box.ROUNDED)
            table.add_column("Neuron Population", style="bold white", width=20)
            table.add_column("Firing Rate", style="bold green", width=15)
            table.add_column("Status Gauge", style="bold yellow")

            # Simulate quick step through brain
            dummy_r = np.random.rand(8*8) * 0.2
            dummy_b = np.random.rand(8*8) * 0.2
            injections = fd.inject(opp=(0, 15), threat=0.2)
            fired = set(brain.step(inject=injections))

            for i, name in enumerate(ACTION_NAMES[:8]):
                pop = populations[i]
                rate = sum(1 for n in pop if n in fired) / len(pop)
                bar_len = int(rate * 20)
                bar_str = "█" * bar_len + "░" * (20 - bar_len)
                table.add_row(name.upper(), f"{rate*100:.1f}%", f"[magenta]{bar_str}[/magenta]")

            stats_panel = Panel(
                f"[bold cyan]Cycle Step:[/] {step}\n"
                f"[bold green]Active Synapses:[/] {len(fired)} / {len(dns)}\n"
                f"[bold yellow]Dopamine Level:[/] {dopamine:+.2f}\n"
                f"[bold magenta]Total Reward:[/] {total_reward:+.1f}",
                title="[bold yellow]🧠 Neural Dynamics[/bold yellow]",
                border_style="green"
            )

            layout = Layout()
            layout.split_row(
                Layout(table, ratio=2),
                Layout(stats_panel, ratio=1)
            )
            return layout

        with Live(generate_telemetry_table(0, 0.0, 0.0), refresh_per_second=10, console=console) as live:
            try:
                while True:
                    step += 1
                    dopamine = learner.dopamine + np.random.normal(0, 0.02)
                    live.update(generate_telemetry_table(step, dopamine, learner.total_reward))
                    time.sleep(0.1)
            except KeyboardInterrupt:
                pass

        console.print("\n[bold green][✓] Telemetry monitor stopped.[/bold green]")

    except ImportError as e:
        print(f"\n[!] Telemetry module error: {e}")
        input("Press Enter to return...")

if __name__ == "__main__":
    run_telemetry()
