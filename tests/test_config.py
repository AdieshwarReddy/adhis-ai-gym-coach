import os
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Main App"))

from services.config.env_config import (
    get_secret,
    is_feature_enabled,
    get_supabase_url,
    get_supabase_anon_key,
    get_groq_api_key,
    get_app_env
)


def test_get_secret_default_when_missing():
    val = get_secret("NON_EXISTENT_KEY_12345", default="fallback_val")
    assert val == "fallback_val"


def test_get_secret_from_env(monkeypatch):
    monkeypatch.setenv("TEST_KEY_ADHI", "test_value_42")
    val = get_secret("TEST_KEY_ADHI")
    assert val == "test_value_42"


def test_is_feature_enabled(monkeypatch):
    monkeypatch.setenv("FEATURE_A", "true")
    monkeypatch.setenv("FEATURE_B", "false")
    assert is_feature_enabled("FEATURE_A") is True
    assert is_feature_enabled("FEATURE_B") is False
    assert is_feature_enabled("FEATURE_MISSING", default=True) is True
