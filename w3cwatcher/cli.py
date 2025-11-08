from __future__ import annotations
from .config import Config, APP_NAME
from .logging import Logger
from .monitor import Monitor
from .notifier import Notifier
from .tray import TrayApp
from .utils.platform import create_tray_shortcut


def main():
    parser = Config.get_argument_parser()
    parser.add_argument('--check', action='store_true', help='Check currently captured rectangle')
    parser.add_argument('--config', action='store_true', help='Open config file')
    parser.add_argument('--tray', action='store_true', help='Run as a system tray app')
    parser.add_argument('--shortcut', action='store_true', help='Create a desktop shortcut for Tray')

    args = parser.parse_args()
    config = Config.from_args()
    logger = Logger.from_config(config)

    notifier = Notifier(
        logger=logger,
        config=config.notifications
    )
    monitor = Monitor(
        logger=logger,
        config=config.monitor,
        notifier=notifier
    )

    if args.config:
        print(config.config_path)
        config.show()
    elif args.shortcut:
        create_tray_shortcut(shortcut_name=f'{APP_NAME}.lnk')
    elif args.check:
        monitor.show_debug_image()
    elif args.tray:
        tray = TrayApp(
            logger=logger,
            config=config.tray,
            monitor=monitor
        )
        tray.run()
    else:
        monitor.run()
