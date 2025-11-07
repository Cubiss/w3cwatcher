from __future__ import annotations
from .config import Config, open_config_file
from .log import init_logging
from .monitor import Monitor
from .notifier import Notifier
from .tray import run_tray, create_tray_shortcut


def main():
    parser = Config.get_argument_parser()
    args = parser.parse_args()

    config = Config.from_args(args)

    logger, log_path = init_logging(config)

    notifier = Notifier(logger)

    if args.config:
        print(config_path())
        open_config_file()
    elif args.shortcut:
        create_tray_shortcut()
    elif args.check:
        Monitor(logger, config, notifier, check_only=True).run()
    elif args.tray:
        run_tray(logger, config, notifier)
    else:
        Monitor(logger, config, notifier).run()