from __future__ import annotations
import json
import requests
from typing import Optional, Dict, Any


def send_discord_webhook(url: str, content: str, embed_fields: Optional[Dict[str, Any]] = None) -> None:
    payload = {"content": content}
    if embed_fields:
        payload["embeds"] = [embed_fields]
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, data=json.dumps(payload), headers=headers, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        print(f"[!] Webhook error: {e}")
