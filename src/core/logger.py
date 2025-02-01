import sys
from typing import Any


def log(message: Any, error: bool = False):
    prefix = "[PLEXY]"
    stream = sys.stderr if error else sys.stdout
    print(f"{prefix} {message}", file=stream)
