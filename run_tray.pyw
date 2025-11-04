#!/usr/bin/env python
import sys
from w3cwatcher.cli import main

if __name__ == "__main__":
    sys.argv.append('--tray')
    main()
