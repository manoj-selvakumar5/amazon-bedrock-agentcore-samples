"""Model loading.

The model id and inference parameters come from the live settings in AppConfig
(model/settings.py); the seam for that is `model_id` and `model_config` being
parameters here, never a hardcoded constant elsewhere.
"""

from typing import Any

from config import DEFAULT_MODEL_ID
from strands.models.bedrock import BedrockModel


def load_model(model_id: str | None = None, model_config: dict[str, Any] | None = None) -> BedrockModel:
    """Return a Bedrock model client using IAM credentials.

    Args:
        model_id: the global inference profile id. Defaults to DEFAULT_MODEL_ID.
        model_config: extra BedrockModel config: the inference parameters from the live
            settings (temperature, max_tokens, top_p), and e.g. {"cache_prompt": "default"}
            to cache a static system prompt.
    """
    return BedrockModel(model_id=model_id or DEFAULT_MODEL_ID, **(model_config or {}))
