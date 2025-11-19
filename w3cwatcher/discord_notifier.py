import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, Callable

import requests

from .config import DiscordConfig
from .logging import Logger
from .state_manager import STATE_IN_GAME


class DiscordNotifier:
    def __init__(self, config: DiscordConfig, logger: Logger):
        self.config = config
        self.logger = logger
        self._discord_webhook_last_sent = 0.0
        self.config.validate_all()

    def _send_discord_webhook(self, content: str, embed_fields: Optional[Dict[str, Any]] = None) -> None:
        now = time.monotonic()
        elapsed = now - self._discord_webhook_last_sent

        if elapsed < self.config.debounce:
            remaining = self.config.debounce - elapsed
            self.logger.info(f"Not sending Discord message (debounced, {remaining:.1f}s remaining)")
            return

        payload: dict[str, Any] = {"content": content}
        if embed_fields:
            payload["embeds"] = [embed_fields]

        headers = {"Content-Type": "application/json"}
        try:
            resp = requests.post(
                self.config.webhook_url,
                data=json.dumps(payload),
                headers=headers,
                timeout=5,
            )
            resp.raise_for_status()
        except Exception as e:
            self.logger.error(f"[!] Webhook error: {e}")

        self._discord_webhook_last_sent = now

    def on_monitor_state_change(self, state, after):
        if state == STATE_IN_GAME:
            self.notify_match_started(queue_duration=after)
            pass

    def notify_match_started(self, queue_duration):
        embed = {
            "title": "W3CWatcher",
            "description": self.config.match_started_message,
            "fields": [],
        }

        if queue_duration:
            time_in_queue_str = (datetime.min + queue_duration).strftime("%H:%M:%S")
            self.logger.info(f"Match started after: {time_in_queue_str}")
            embed["fields"].append(
                {
                    "name": "Time in Queue",
                    "value": str(time_in_queue_str),
                    "inline": True,
                }
            )

        self._send_discord_webhook("", embed)