"""Data pipeline package initialization.

Expose common submodules (e.g., :mod:`market_data`) via lazy imports to
avoid side effects on package import.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING, Any

# Public API surface
__all__: tuple[str, ...] = (
    "market_data",
    "compute_factors",
    "db_utils",
    "config",
)


def __getattr__(name: str) -> ModuleType:
    """Lazily import known submodules on first attribute access."""
    if name in __all__:
        mod = import_module(f"{__name__}.{name}")
        globals()[name] = mod  # cache for subsequent lookups
        return mod
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Improve IDE/tab completion by listing public attributes."""
    return sorted(list(globals().keys()) + list(__all__))


# Make static analyzers aware of the submodules without changing runtime behavior.
if TYPE_CHECKING:
    from . import compute_factors, config, db_utils, market_data  # noqa: F401
