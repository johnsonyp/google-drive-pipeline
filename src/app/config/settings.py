from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str | None = "dev"
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    RAW_FOLDER_ID: str | None = None
    PROCESSED_FOLDER_ID: str | None = None
    
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()