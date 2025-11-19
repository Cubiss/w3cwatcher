import time
from datetime import datetime
from typing import Any

import requests

from .config import TelegramConfig
from .logging import Logger
from .state_manager import STATE_IN_GAME


class TelegramNotifier:
    def __init__(self, config: TelegramConfig, logger: Logger):
        self.config = config
        self.logger = logger
        self._telegram_last_sent = 0.0

        self.api_url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"

        self.config.validate_all()

    def _send_telegram_message(self, text: str) -> None:
        now = time.monotonic()
        elapsed = now - self._telegram_last_sent

        if elapsed < self.config.debounce:
            remaining = self.config.debounce - elapsed
            self.logger.info(f"Not sending Telegram message (debounced, {remaining:.1f}s remaining)")
            return

        data: dict[str, Any] = {
            "chat_id": self.config.chat_id,
            "text": text,
        }

        try:
            resp = requests.post(self.api_url, data=data, timeout=5)
            resp.raise_for_status()
        except Exception as e:
            self.logger.error(f"Telegram error: {e}")

        self._telegram_last_sent = now

    def on_monitor_state_change(self, state, after):
        if state == STATE_IN_GAME:
            self.notify_match_started(queue_duration=after)

    def notify_match_started(self, queue_duration):
        lines = [self.config.match_started_message]

        if queue_duration:
            time_in_queue_str = (datetime.min + queue_duration).strftime("%H:%M:%S")
            self.logger.info(f"Match started after: {time_in_queue_str}")
            lines.append(f"Time in Queue: {time_in_queue_str}")

        message = "\n".join(lines)
        self._send_telegram_message(message)
