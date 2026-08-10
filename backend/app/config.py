from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_model: str = "cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit"
    vllm_api_key: str = "EMPTY"
    request_timeout_seconds: float = 120.0
    api_tokens: str = "factory-dev-token"
    api_log_path: str = "logs/api_calls.jsonl"
    api_rate_limit_requests: int = 60
    api_rate_limit_window_seconds: int = 60
    admin_password: str = "factory-admin"
    admin_session_token: str = "factory-admin-session"
    vision_enabled: bool = False

    model_config = SettingsConfigDict(env_prefix="", env_file=".env")


class AppInfo(BaseModel):
    name: str = "Factory AI Platform"
    version: str = "0.1.0"


settings = Settings()
app_info = AppInfo()
