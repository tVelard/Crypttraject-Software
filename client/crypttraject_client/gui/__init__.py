"""Desktop GUI (PySide6) for the CryptTraject client.

Run:
    python -m crypttraject_client.gui
or
    crypttraject-gui    # console_scripts entrypoint
"""

from .main_window import MainWindow, run

__all__ = ["MainWindow", "run"]
