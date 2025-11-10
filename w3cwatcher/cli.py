from __future__ import annotations

import tomlkit

from .config import load_config, APP_NAME
from .logging import Logger
from .monitor import Monitor
from .notifier import Notifier
from .tray import TrayApp
from .utils.platform import create_tray_shortcut


def main():
    args, config = load_config()
    logger = Logger.from_config(config.logging)

    doc = config.as_toml(include_defaults=True, comment="source")
    logger.debug(tomlkit.dumps(doc))

    errors, message = config.validate_all(raise_error=False)
    logger.warning(message)

    notifier = Notifier(logger=logger, config=config.notifications)
    monitor = Monitor(logger=logger, config=config.monitor, notifier=notifier)

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
