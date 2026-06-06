"""Desktop GUI for the CryptTraject client.

A thin PySide6 front-end over the exact same privacy-preserving pipeline
as the CLI: data is hashed and BFV-encrypted locally, only ciphertexts
are uploaded, the server computes on ciphertexts, and decryption +
clustering + visualisation all happen on this machine.

Entry point: `crypttraject_client.gui.main_window.run`.
"""

from .main_window import run

__all__ = ["run"]
