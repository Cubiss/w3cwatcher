import re
from typing import Callable

_WEBHOOK_RE = re.compile(
    r"^https://discord\.com/api/webhooks/(?P<webhook_id>\d+)/(?P<webhook_token>[A-Za-z0-9._-]+)$"
)


def get_discord_webhook_secret_redactor(url: str, *, mask: str = "****") -> Callable[[str], str]:
    m = _WEBHOOK_RE.match(url)
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
