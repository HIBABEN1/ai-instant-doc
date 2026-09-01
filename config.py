

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    TEMPLATE_PATH: str = "template_capgemini.docx"
    OUTPUT_FOLDER: str = "data/processed/"

    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()