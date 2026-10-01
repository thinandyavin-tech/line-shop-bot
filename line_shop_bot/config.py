from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    line_channel_secret: str
    line_access_token: str
    promptpay_id: str
    app_base_url: str
    owner_user_id: str = ""
    menu_path: str = "menu.example.json"
    database_path: str = "orders.db"
    llm_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"
    llm_base_url: str = "https://api.groq.com/openai/v1"

    @classmethod
    def from_env(cls) -> Settings:
        def req(name: str) -> str:
            value = os.environ.get(name, "").strip()
            if not value:
                raise RuntimeError(f"missing required environment variable {name}")
            return value

        return cls(
            line_channel_secret=req("LINE_CHANNEL_SECRET"),
            line_access_token=req("LINE_CHANNEL_ACCESS_TOKEN"),
            promptpay_id=req("PROMPTPAY_ID"),
            app_base_url=req("APP_BASE_URL").rstrip("/"),
            owner_user_id=os.environ.get("OWNER_USER_ID", ""),
            menu_path=os.environ.get("MENU_PATH", "menu.example.json"),
            database_path=os.environ.get("DATABASE_PATH", "orders.db"),
            llm_api_key=os.environ.get("LLM_API_KEY", ""),
            llm_model=os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile"),
            llm_base_url=os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
        )
