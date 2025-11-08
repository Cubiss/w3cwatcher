from __future__ import annotations
import json
import time
from datetime import datetime

from .config import NotificationsConfig
from .logging import Logger

import requests
from typing import Optional, Dict, Any, Callable

from w3cwatcher.utils import get_discord_webhook_secret_redactor


class Notifier:
    def __init__(self, logger: Logger,
                 config: NotificationsConfig,
                 ):
        self.match_started_message = config.match_started_message
        self.discord_webhook_debounce = config.discord_debounce
        self._discord_webhook_last_sent = 0.0
        self.discord_webhook_url =  config.discord_webhook_url
        logger.add_redactor(get_discord_webhook_secret_redactor(config.discord_webhook_url))
        self.l = logger

    def _send_discord_webhook(self, content: str, embed_fields: Optional[Dict[str, Any]] = None) -> None:
        now = time.monotonic()
        elapsed = now - self._discord_webhook_last_sent

        if elapsed < self.discord_webhook_debounce:
            remaining = self.discord_webhook_debounce - elapsed
            self.l.info(f"Not sending Discord message (debounced, {remaining:.1f}s remaining)")
            return

        payload: dict[str, Any] = {"content": content}
        if embed_fields:
            payload["embeds"] = [embed_fields]

        headers = {"Content-Type": "application/json"}
        try:
            resp = requests.post(self.discord_webhook_url, data=json.dumps(payload), headers=headers, timeout=5)
            resp.raise_for_status()
        except Exception as e:
            self.l.error(f"[!] Webhook error: {e}")

        self._discord_webhook_last_sent = now

    def notify_match_started(self, queue_duration):
        embed = {
            "title": "W3CWatcher",
            "description": self.match_started_message,
            "fields": [
            ],
        }

        if queue_duration:
            time_in_queue_str = (datetime.min + queue_duration).strftime("%H:%M:%S")
            self.l.info(f"Match started after: {time_in_queue_str}")
            embed["fields"].append({"name": "Time in Queue", "value": str(time_in_queue_str), "inline": True})


        self._send_discord_webhook('', embed)
