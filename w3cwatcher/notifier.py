from __future__ import annotations
import json
from logging import Logger

import requests
from typing import Optional, Dict, Any


class Notifier:
    def __init__(self, logger: Logger, discord_webhook_url: str = None):
        self.discord_webhook_url = discord_webhook_url
        self.l = logger


    def _send_discord_webhook(self, content: str, embed_fields: Optional[Dict[str, Any]] = None) -> None:
        payload = {"content": content}
        if embed_fields:
            payload["embeds"] = [embed_fields]
        headers = {"Content-Type": "application/json"}
        try:
            resp = requests.post(self.discord_webhook_url, data=json.dumps(payload), headers=headers, timeout=5)
            resp.raise_for_status()
        except Exception as e:
            self.l.error(f"[!] Webhook error: {e}")


    def notify(self, content: str, embed_fields: Optional[Dict[str, Any]] = None):
        self._send_discord_webhook(content, embed_fields)

