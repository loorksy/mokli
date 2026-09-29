"""Process configuration. Secrets come from the environment, never from source."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mokli_host: str = "127.0.0.1"
    mokli_port: int = 8787
    mokli_live: str = "0"
    mokli_data_dir: str = ""
    mokli_passphrase: str = "mokli-dev-passphrase"
    mokli_fernet_key: str = ""
    mokli_cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    mokli_heartbeat_minutes: int = 15
    mokli_totp_enabled: str = "0"

    oanda_api_token: str = ""
    oanda_account_id: str = ""
    oanda_env: str = "practice"

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    openrouter_api_key: str = ""
    openrouter_model: str = ""
    kimi_api_key: str = ""
    kimi_model: str = "kimi-k2-turbo-preview"
    kimi_base_url: str = "https://api.moonshot.ai/v1"
    zai_api_key: str = ""
    zai_model: str = "glm-4.5"
    zai_agent_id: str = ""
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = ""

    metaapi_token: str = ""
    metaapi_account_id: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    fcm_server_key: str = ""

    fallback_provider: str = "mokli"
    active_provider: str = "mokli"

    point_size: float = 0.01
    contract_ounces: float = 100.0
    paper_balance: float = 10_000.0
    paper_slippage_points: float = 2.0

    display_timezone: str = "Asia/Riyadh"

    @property
    def data_dir(self) -> Path:
        if self.mokli_data_dir:
            return Path(self.mokli_data_dir).expanduser()
        return Path.home() / ".mokli"

    @property
    def workspace_dir(self) -> Path:
        return self.data_dir / "workspace"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "mokli.db"

    @property
    def live_flag(self) -> bool:
        return self.mokli_live == "1"

    @property
    def cors_list(self) -> list[str]:
        return [item.strip() for item in self.mokli_cors_origins.split(",") if item.strip()]


def load_settings() -> Settings:
    return Settings()
