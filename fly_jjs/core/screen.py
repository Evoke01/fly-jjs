"""Finding the game window on screen."""

FALLBACK_MONITOR = {"top": 240, "left": 560, "width": 800, "height": 600}
TITLES = ("roblox", "sober", "jujutsu")


def detect_monitor():
    """Capture region of the game window (inside its title bar), or a fallback region."""
    print("\n[System] Searching for game window...")
    try:
        import pygetwindow as gw
        windows = [
            w for w in gw.getAllWindows()
            if any(t in w.title.lower() for t in TITLES) and w.width > 100 and w.height > 100
            # Minimised windows report a position around -32000 and can't be captured.
            and not getattr(w, "isMinimized", False) and w.left > -30000 and w.top > -30000
        ]
        if windows:
            windows.sort(key=lambda w: w.width * w.height, reverse=True)
            win = windows[0]
            # No clamping to 0: a monitor left of / above the main one has negative
            # coordinates, and mss captures those fine.
            monitor = {
                "top": win.top + 40,
                "left": win.left + 5,
                "width": win.width - 10,
                "height": win.height - 45,
            }
            print(f"[System] Found window '{win.title}': {monitor['width']}x{monitor['height']}")
            return monitor
    except Exception:
        pass
    print("[System] Game window not found. Using screen bounds fallback.")
    return dict(FALLBACK_MONITOR)
