import importlib

import pytest


def test_loader_requires_api_key(monkeypatch):
    monkeypatch.delenv("QUANDL_API_KEY", raising=False)
    module = importlib.reload(importlib.import_module("data_pipeline.Macro_data"))
    with pytest.raises(
        ValueError, match="QUANDL_API_KEY is not configured"
    ):
        module.FiveYearMacroDataLoader()

