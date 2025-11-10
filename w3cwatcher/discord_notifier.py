import json
import re
import time
from datetime import datetime
from typing import Optional, Dict, Any, Callable

import requests

from .config import DiscordConfig
from .logging import Logger
from .statemanager import STATE_DISABLED, STATE_WAITING, STATE_IN_QUEUE, STATE_IN_GAME


class DiscordNotifier:
    def __init__(self, config: DiscordConfig, logger: Logger):
        self.config = config
        self.logger = logger
        self._discord_webhook_last_sent = 0.0


        self.config.validate_all()
        # noinspection PyBroadException
        try:
            logger.add_redactor(self.create_discord_webhook_redactor(config.webhook_url))
        except Exception:
            logger.warning("Failed to add discord url redactor.")

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

    @staticmethod
    def create_discord_webhook_redactor(url: str, *, mask: str = "****") -> Callable[[str], str]:
        m = re.match(
            r"^https://discord\.com/api/webhooks/(?P<webhook_id>\d+)/(?P<webhook_token>[A-Za-z0-9._-]+)$",
                 url)
        if not m:
            expected_format = "https://discord.com/api/webhooks/{webhook_id}/{webhook_token}"
            raise ValueError(f"Expected format: {expected_format}")

        webhook_id = m.group("webhook_id")
        webhook_token = m.group("webhook_token")

        def redact(text: str) -> str:
            if not text:
                return text
            return text.replace(webhook_token, mask).replace(webhook_id, mask)

        return redact
