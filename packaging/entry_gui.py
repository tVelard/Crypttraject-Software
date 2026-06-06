"""Entry point for the PyInstaller GUI bundle.

A trivial wrapper so PyInstaller has a concrete script to freeze instead of
having to resolve a gui_scripts entry. Don't add logic here — keep behavior
changes in `crypttraject_client.gui`.
"""

import sys

from crypttraject_client.gui import run

if __name__ == "__main__":
    sys.exit(run())
