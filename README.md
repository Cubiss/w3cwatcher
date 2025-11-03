# W3C Watcher

W3C Watcher is a lightweight background pixel-monitoring utility for
Windows.\
It checks for the color of the W3Champions match button and sends a discord notification when it detects change from in-queue to not-in-queue. 

------------------------------------------------------------------------

## 📦 Installation
``` bash
pip install git+https://github.com/Cubiss/w3cwatcher.git
```

------------------------------------------------------------------------

## Usage

### GUI / Tray Mode

Run normally to start the tray watcher:

``` bash
w3cwatcher --tray
```

Right-click the tray icon to configure:
-   Start - starts monitoring (Icon turns green if successful)  
-   Stop - stops monitoring
-   Tools/Check - opens image showing what w3champion sees  
-   Tools/Log - opens log console
-   Tools/Settings -opens settings file

### CLI Mode

``` bash
usage: w3cwatcher [-h] [--title TITLE] [--x X] [--y Y] [--poll POLL] [--debounce DEBOUNCE] [--message MESSAGE]
                  [--webhook WEBHOOK] [--tray] [--check] [--config]

Watch a pixel in a window and notify via Discord

options:
  -h, --help           show this help message and exit
  --title TITLE        Substring to match target window title
  --x X                Client X offset (0.5 = middle, 1.0 = left)
  --y Y                Client Y offset (0.5 = middle), 1.0 = bottom
  --poll POLL          Polling rate (s)
  --debounce DEBOUNCE  Minimum seconds between webhooks
  --message MESSAGE    Discord message content
  --webhook WEBHOOK    Discord webhook URL (overrides env/file)
  --tray               Run as a system tray app
  --check              Check currently captured rectangle
  --config             Opens config file
```