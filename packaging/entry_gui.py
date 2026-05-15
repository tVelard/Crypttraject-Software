"""Entry point for the PyInstaller GUI bundle."""

import sys

from crypttraject_client.gui.main_window import run

if __name__ == "__main__":
    sys.exit(run())
