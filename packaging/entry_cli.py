"""Entry point for the PyInstaller CLI bundle.

A trivial wrapper so PyInstaller has a concrete script to freeze instead
of having to resolve a console_scripts entry. Don't add logic here — keep
behavior changes in `crypttraject_client.cli`.
"""

import sys

from crypttraject_client.cli import main

if __name__ == "__main__":
    sys.exit(main())
