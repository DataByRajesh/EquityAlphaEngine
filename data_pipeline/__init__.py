"""Data pipeline package initialization.

Adds the package directory to ``sys.path`` so legacy imports like
``import market_data`` continue to work.  Common submodules are exposed
via ``__all__`` and imported lazily to avoid side effects during package
import."""

from importlib import import_module
from pathlib import Path
from typing import Any
import sys

_PACKAGE_DIR = Path(__file__).resolve().parent
if str(_PACKAGE_DIR) not in sys.path:
    sys.path.append(str(_PACKAGE_DIR))

__all__ = ["streamlit_screener"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        return import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
