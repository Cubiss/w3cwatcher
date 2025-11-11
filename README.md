# W3C Watcher

W3C Watcher is a lightweight background pixel-monitoring utility for
Windows.\
It checks for the color of the W3Champions match button and sends a discord notification when it detects change from in-queue to not-in-queue. 

Currently supports Windows only.  

------------------------------------------------------------------------

## Installation
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
-   Tools/Check - opens image showing what W3CWatcher sees  
-   Tools/Log - tails log file
-   Tools/Settings - opens settings file

Icon color:
- Green - Ready
- Red - In Queue
- Grey - Disabled

### CLI Mode

``` bash
usage: w3cwatcher [-h] [--title TITLE] [--x X] [--y Y] [--poll POLL] [--debounce DEBOUNCE] [--message MESSAGE] [--webhook WEBHOOK] [--tray]
                  [--check] [--config] [--shortcut]

Watch a pixel in a window and notify via Discord

options:
  -h, --help           show this help message and exit
  --webhook WEBHOOK    Discord webhook URL
  --tray               Run as a system tray app
  --check              Check currently captured rectangle
  --config             Opens config file
  --shortcut           Creates a desktop shortcut
```

## Setup a Discord webhook

1.  Open **Discord**
2.  Go to the server and **select the channel**
3.  Click the channel name → **Integrations**
    -   (Alternate) Right‑click channel → **Edit Channel** →
        **Integrations**
4.  Click **Webhooks**
5.  Click **New Webhook**
6.  Name it and pick the channel
7.  Click **Copy Webhook URL**
8.  Run `w3cwatcher --settings` or click `Tools/Settings` in Tray context menu
9.  Paste your url into `discord_webhook_url` field

The config file should look like this:
```toml config.toml
[notifications.discord]
webhook_url = "https://discord.com/api/webhooks/.../..."
```
