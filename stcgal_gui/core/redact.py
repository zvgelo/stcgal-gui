"""Redakcja danych wrażliwych z logów przed kopiowaniem/eksportem."""

from __future__ import annotations

import getpass
import os
import re
import socket
from collections.abc import Iterable


def redact(text: str, extra_secrets: Iterable[str] = ()) -> str:
    """Zastępuje katalog domowy, nazwę użytkownika/hosta i numery seryjne USB."""
    home = os.path.expanduser("~")
    if home and home != "/":
        text = text.replace(home, "~")
    try:
        user = getpass.getuser()
    except (KeyError, OSError):
        user = ""
    host = socket.gethostname()
    for secret, repl in ((user, "<user>"), (host, "<host>")):
        if secret and len(secret) > 2:
            text = re.sub(rf"(?<![\w-]){re.escape(secret)}(?![\w-])", repl, text)
    for s in extra_secrets:
        if s:
            text = text.replace(s, "<serial>")
    text = re.sub(r"(usb-[^\s/]*?_)([A-Za-z0-9]{6,})(-if\d+)", r"\1<serial>\3", text)
    return text
