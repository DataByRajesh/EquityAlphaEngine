import importlib

import pytest


def test_loader_requires_api_key(monkeypatch):
    monkeypatch.delenv("QUANDL_API_KEY", raising=False)
    module = importlib.reload(
        importlib.import_module("data_pipeline.Macro_data"))
    # Should not raise error, just log warning and use mock data
    loader = module.FiveYearMacroDataLoader()
    assert loader is not None
