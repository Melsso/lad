from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str
    DB_PORT: int = 5432

    DEBUG: bool = False

    SUMMARY_THRESHOLD: int = 20
    RECENT_MESSAGES_TO_KEEP: int = 8

    OLLAMA_HOST: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "qwen3:8b"
    OLLAMA_TIMEOUT: float = 120.0

    MCP_SERVERS: str = "[]"
    MAX_TOOL_ITERATIONS: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


conf = Settings()
