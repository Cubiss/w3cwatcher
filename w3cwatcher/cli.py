from __future__ import annotations

import tomlkit

from .config import load_config, APP_NAME
from .discord_notifier import DiscordNotifier
from .logging import Logger
from .monitor import Monitor
from .statemanager import StateManager
from .tray import TrayApp
from .utils.platform import create_tray_shortcut


def main():
    args, config = load_config()
    logger = Logger.from_config(config.logging)

    doc = config.as_toml(include_defaults=True, comment="source")
    logger.debug(tomlkit.dumps(doc))

    errors, message = config.validate_all(raise_error=False)
    logger.warning(message)

    state_manager = StateManager(logger=logger)
    monitor = Monitor(logger=logger, config=config.monitor, state_manager=state_manager)
    notifier = DiscordNotifier(config=config.notifications.discord, logger=logger)
    state_manager.add_state_change_listener(notifier.on_monitor_state_change)

    if args.config:
        pass
    elif args.shortcut:
        create_tray_shortcut(shortcut_name=f"{APP_NAME}.lnk")
    elif args.check:
        monitor.show_debug_image()
    elif args.tray:
        tray = TrayApp(logger=logger, config=config.tray, monitor=monitor)
        tray.run()
    else:
        monitor.run()
