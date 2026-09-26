"""The live model settings: the AppConfig document in, {model_id, params} out.

resolve_settings is pure, so these need no AWS.
"""

from config import DEFAULT_MODEL_ID
from model.settings import get_model_settings, resolve_settings


def test_model_id_and_all_parameters():
    settings = resolve_settings(
        {"modelId": "global.anthropic.claude-sonnet-4-6", "temperature": 0.2, "maxTokens": 4096, "topP": 0.9}
    )
    assert settings == {
        "model_id": "global.anthropic.claude-sonnet-4-6",
        "params": {"temperature": 0.2, "max_tokens": 4096, "top_p": 0.9},
    }


def test_parameters_left_out_keep_the_model_defaults():
    settings = resolve_settings({"modelId": "global.anthropic.claude-opus-4-8"})
    assert settings["params"] == {}


def test_missing_model_id_falls_back_to_the_default():
    assert resolve_settings({"temperature": 0.5})["model_id"] == DEFAULT_MODEL_ID
    assert resolve_settings({"modelId": ""})["model_id"] == DEFAULT_MODEL_ID


def test_malformed_parameters_are_ignored():
    settings = resolve_settings({"modelId": "m", "temperature": "hot", "maxTokens": True, "topP": None})
    assert settings["params"] == {}


def test_max_tokens_is_an_integer():
    assert resolve_settings({"maxTokens": 2048.0})["params"] == {"max_tokens": 2048}


def test_malformed_document_falls_back_to_defaults():
    for bad in (None, [], "text", 3):
        assert resolve_settings(bad) == {"model_id": DEFAULT_MODEL_ID, "params": {}}


def test_without_appconfig_the_defaults_are_used(monkeypatch):
    import model.settings as settings_module

    monkeypatch.setattr(settings_module, "APPCONFIG_APPLICATION", "")
    assert get_model_settings() == {"model_id": DEFAULT_MODEL_ID, "params": {}}
