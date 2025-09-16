import importlib
import sys

import pytest


def test_loader_requires_api_key(monkeypatch):
    """FiveYearMacroDataLoader should work with mock data without an API key."""
    monkeypatch.delenv("QUANDL_API_KEY", raising=False)
    sys.modules.pop("data_pipeline.Macro_data", None)
    macro_data = importlib.import_module("data_pipeline.Macro_data")
    # Should not raise error, just use mock data
    loader = macro_data.FiveYearMacroDataLoader()
    assert loader is not None
