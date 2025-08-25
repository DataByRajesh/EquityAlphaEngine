import importlib
import sys

import pytest


def test_loader_requires_api_key(monkeypatch):
    """FiveYearMacroDataLoader should fail fast without an API key."""
    monkeypatch.delenv("QUANDL_API_KEY", raising=False)
    sys.modules.pop("data_pipeline.Macro_data", None)
    macro_data = importlib.import_module("data_pipeline.Macro_data")
    with pytest.raises(ValueError, match="QUANDL_API_KEY"):
        macro_data.FiveYearMacroDataLoader()
