import json
import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value or ""


@dataclass
class Settings:
    whatsapp_token: str
    phone_number_id: str
    verify_token: str
    app_secret: str
    admin_token: str
    owner_number: str = ""
    graph_api_version: str = "v22.0"
    claude_model: str = "claude-opus-5-5"
    claude_effort: str = "low"
    db_path: str = "bot.db"
    business: dict = field(default_factory=dict)
    history_messages: int = 20

    @classmethod
    def from_env(cls) -> "Settings":
        business_file = Path(_env("BUSINESS_FILE", "business.json"))
        if not business_file.exists():
            raise RuntimeError(
                f"{business_file} not found - copy business.example.json and fill in your business"
            )
        return cls(
            whatsapp_token=_env("WHATSAPP_TOKEN", required=True),
            phone_number_id=_env("WHATSAPP_PHONE_NUMBER_ID", required=True),
            verify_token=_env("WHATSAPP_VERIFY_TOKEN", required=True),
            app_secret=_env("WHATSAPP_APP_SECRET", required=True),
            admin_token=_env("ADMIN_TOKEN", required=True),
            owner_number=_env("OWNER_WHATSAPP_NUMBER", ""),
            graph_api_version=_env("GRAPH_API_VERSION", "v22.0"),
            claude_model=_env("CLAUDE_MODEL", "claude-opus-5-5"),
            claude_effort=_env("CLAUDE_EFFORT", "low"),
            db_path=_env("DB_PATH", "bot.db"),
            business=json.loads(business_file.read_text(encoding="utf-8")),
        )
