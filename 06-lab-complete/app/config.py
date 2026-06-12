"""Production config — 12-Factor: tất cả lấy từ environment variables."""
import os
from dataclasses import dataclass, field

try:
    # Tiện cho local dev — load .env nếu có. Production dùng env thật.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv là optional
    pass


@dataclass
class Settings:
    # Server
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    # App
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "Travel Chatbot API"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))

    # LLM
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-3.5-turbo"))

    # CORS / Security
    allowed_origins: list = field(
        default_factory=lambda: os.getenv("CORS_ORIGINS", "*").split(",")
    )

    # Observability
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    @property
    def llm_mode(self) -> str:
        key = self.openai_api_key
        return "openai" if key and key != "your_openai_api_key_here" else "rule-based"


settings = Settings()
