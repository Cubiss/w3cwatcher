# Pixel Watcher

A small Windows utility that watches a specific pixel inside a target window's **client area** and triggers a Discord webhook when a match condition is met. Includes:

- Installable Python package (pip/pyproject)
- Command-line interface with flags
- System tray app (Windows) with start/stop and calibrate
- Simple color name helper for log readability

## Install (dev)
```bash
pip install -e .
```

## CLI examples
```bash
# Run with defaults from config
pixel-watcher

# Override offsets and target
pixel-watcher --x 1960 --y 1358 --target 117,12,16 --tol 15 --title W3Champions

# Fire only on change and set debounce to 30s
pixel-watcher --change-only --debounce 30
```

## Tray app
```bash
pixel-watcher --tray
```

Environment variables:
- `DISCORD_WEBHOOK_URL` — webhook URL (or put plaintext at `~/webhook`)

## Notes
- Coordinates are *client* offsets; use **Calibrate** from the tray or `--calibrate` in CLI.
