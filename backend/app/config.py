"""Settings, loaded from environment variables (see .env.example)."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    lm_studio_base_url: str = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    lm_studio_api_key: str = os.getenv("LM_STUDIO_API_KEY", "lm-studio")  # LM Studio ignores this value but the OpenAI SDK requires a non-empty string
    lm_studio_model: str = os.getenv("LM_STUDIO_MODEL", "prism-ml/bonsai-27b")
    request_timeout_seconds: float = float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "120"))
    max_context_chars: int = int(os.getenv("MAX_CONTEXT_CHARS", "24000"))
    port: int = int(os.getenv("PORT", "8000"))
    cors_origins: list[str] = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080",
    ).split(",")


settings = Settings()
