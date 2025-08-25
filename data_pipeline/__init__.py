"""Data pipeline package initialization.

Expose common submodules such as :mod:`market_data` while allowing lazy
imports to avoid side effects during package import.
"""

from importlib import import_module
from typing import Any

# Commonly used submodules are defined here for convenient access while
# still allowing lazy importing via ``__getattr__``.
__all__: list[str] = [
    "market_data",
    "compute_factors",
    "db_utils",
    "config",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        return import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
