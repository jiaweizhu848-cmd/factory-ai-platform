from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_model: str = "cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit"
    vllm_api_key: str = "EMPTY"
    request_timeout_seconds: float = 120.0

    model_config = SettingsConfigDict(env_prefix="", env_file=".env")


class AppInfo(BaseModel):
    name: str = "Factory AI Platform"
    version: str = "0.1.0"


settings = Settings()
app_info = AppInfo()
