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

## Setup a Discord webhook

1.  Open **Discord**
2.  Go to the server and **select the channel**
3.  Click the channel name → **Integrations**
    -   (Alternate) Right‑click channel → **Edit Channel** →
        **Integrations**
4.  Click **Webhooks**
5.  Click **New Webhook**
6.  Name it and pick the channel
7.  Click **Copy Webhook URL**. This is your `webhook_url`.
8.  Run `w3cwatcher --settings` or click `Tools/Settings` in Tray context menu to open the config file
9.  Add or update the Discord section:

```toml config.toml
[notifications.discord]
enabled = true
webhook_url = "https://discord.com/api/webhooks/.../..."
```

## Setup a Telegram Bot

1.  **Open Telegram**
2.  Search for **`@BotFather`** and start a chat
3.  Create a new bot by sending: `/newbot`
4.  Choose a **name** and a **username** (the username must end with `bot`, e.g. `w3cwatcher_notifier_bot`)
5.  BotFather will reply with your **Bot Token**, for example: `123456789:ABCdefGhIjkLmNoPQRstuVWxyZ`. This is your `bot_token` 
6.  In Telegram, search for **`@userinfobot`**  
7.  Start it, and it will immediately display your **Telegram user ID**. This is your `chat_id`
8.  Run `w3cwatcher --settings` or click `Tools/Settings` in Tray context menu to open the config file
9.  Add or update the Telegram section:
```toml
[notifications.telegram]
enabled = true
bot_token = "123456789:ABCdefGhIjkLmNoPQRstuVWxyZ"
chat_id = "123456789"
```
