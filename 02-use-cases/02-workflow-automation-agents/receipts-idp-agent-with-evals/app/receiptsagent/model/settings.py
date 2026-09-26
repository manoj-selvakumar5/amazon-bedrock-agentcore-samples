"""Model settings, read live from AppConfig.

The model id and its inference parameters live in an AppConfig freeform profile, so
they can be changed by deploying a new configuration version, with no redeploy of the
agent (ADR-0008). The agent runs in a CONTAINER (not a Lambda), so it reads AppConfig
via the `appconfigdata` data API directly (StartConfigurationSession ->
GetLatestConfiguration), NOT the Lambda Agent extension (ADR-0009). Config is cached
in-process and only re-polled after the server-provided NextPollInterval.

Config shape:
{
  "modelId": "global.anthropic.claude-opus-4-8",
  "temperature": 0.2,      # optional
  "maxTokens": 4096,       # optional
  "topP": 0.9              # optional
}

A parameter left out keeps the model's default. If AppConfig is unset, unreachable or
malformed, the agent runs on DEFAULT_MODEL_ID with the model's defaults: it never
hard-fails because it could not read its settings.
"""

import json
import time
from typing import Any

from config import (
    APPCONFIG_APPLICATION,
    APPCONFIG_ENVIRONMENT,
    APPCONFIG_PROFILE,
    DEFAULT_MODEL_ID,
    REGION,
)

# AppConfig key -> Strands BedrockModel config key.
INFERENCE_PARAMS = {"temperature": "temperature", "maxTokens": "max_tokens", "topP": "top_p"}

DEFAULT_SETTINGS: dict[str, Any] = {"model_id": DEFAULT_MODEL_ID, "params": {}}

# Module-level cache: (parsed config, token, expires_at).
_cache: dict[str, Any] = {"value": None, "token": None, "expires_at": 0.0}


def resolve_settings(config: Any) -> dict[str, Any]:
    """Pure: turn the AppConfig document into {model_id, params}.

    params holds only the inference parameters present and well-typed, already named
    for BedrockModel. Anything missing or malformed falls back to the defaults.
    """
    if not isinstance(config, dict):
        return {**DEFAULT_SETTINGS, "params": {}}
    model_id = config.get("modelId")
    if not isinstance(model_id, str) or not model_id:
        model_id = DEFAULT_MODEL_ID
    params: dict[str, Any] = {}
    for key, bedrock_key in INFERENCE_PARAMS.items():
        value = config.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        params[bedrock_key] = int(value) if key == "maxTokens" else float(value)
    return {"model_id": model_id, "params": params}


def _appconfig_configured() -> bool:
    return bool(APPCONFIG_APPLICATION and APPCONFIG_ENVIRONMENT and APPCONFIG_PROFILE)


def _fetch_config() -> dict[str, Any] | None:
    """Read the latest settings via the appconfigdata data API. Returns the parsed
    dict, or the last cached value when AppConfig reports no change."""
    import boto3

    client = boto3.client("appconfigdata", region_name=REGION)
    token = _cache.get("token")
    if not token:
        token = client.start_configuration_session(
            ApplicationIdentifier=APPCONFIG_APPLICATION,
            EnvironmentIdentifier=APPCONFIG_ENVIRONMENT,
            ConfigurationProfileIdentifier=APPCONFIG_PROFILE,
        )["InitialConfigurationToken"]

    resp = client.get_latest_configuration(ConfigurationToken=token)
    _cache["token"] = resp["NextPollConfigurationToken"]
    _cache["expires_at"] = time.monotonic() + int(resp.get("NextPollIntervalInSeconds", 60))

    raw = resp["Configuration"].read()
    if raw:  # empty body => unchanged since last poll; keep cached value
        _cache["value"] = json.loads(raw)
    return _cache["value"]


def get_model_settings() -> dict[str, Any]:
    """Return {model_id, params}, reading AppConfig (cached) when configured, else the
    defaults. Never raises."""
    if not _appconfig_configured():
        return {**DEFAULT_SETTINGS, "params": {}}
    try:
        if _cache["value"] is None or time.monotonic() >= _cache["expires_at"]:
            cfg = _fetch_config()
        else:
            cfg = _cache["value"]
        return resolve_settings(cfg)
    except Exception:
        return {**DEFAULT_SETTINGS, "params": {}}
