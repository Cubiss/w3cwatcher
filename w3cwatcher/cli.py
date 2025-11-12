from __future__ import annotations

import tomlkit

from .config import load_config, APP_NAME
from .discord_notifier import DiscordNotifier
from .logging import Logger
from .monitor import Monitor
from .state_manager import StateManager
from .tray import TrayApp


def main():
    args, config = load_config()
    logger = Logger.from_config(config.logging)

    doc = config.as_toml(include_defaults=True, comment="source")
    logger.debug(tomlkit.dumps(doc))

    errors, message = config.validate_all(raise_error=False)
    if len(errors) > 0:
        logger.warning(message)

    state_manager = StateManager(logger=logger)
    monitor = Monitor(logger=logger, config=config.monitor, state_manager=state_manager)
    notifier = DiscordNotifier(config=config.notifications.discord, logger=logger)
    state_manager.add_state_change_listener(notifier.on_monitor_state_change)

    if args.check:
        monitor.show_debug_image()
    elif args.tray:
        tray = TrayApp.create_singleton(logger=logger, config=config.tray, monitor=monitor)
        tray.run()
    else:
        monitor.run()
