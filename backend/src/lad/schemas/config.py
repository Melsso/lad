from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str
    DB_PORT: int = 5432

    DEBUG: bool = False

    SUMMARY_THRESHOLD: int = 20
    RECENT_MESSAGES_TO_KEEP: int = 8

    GEMINI_API_KEY: str
    GEMINI_MODEL: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


conf = Settings()
