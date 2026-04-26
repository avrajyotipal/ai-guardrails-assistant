from pathlib import Path
from pydantic_settings import BaseSettings

# .env lives one level above this file (project root)
_ENV_FILE = str(Path(__file__).parent.parent / ".env")


class Settings(BaseSettings):
    SUPABASE_URL: str = ""
    DATABASE_URL: str = ""
    EURI_API_KEY: str = ""
    EURI_BASE_URL: str = "https://api.euron.one/api/v1/euri"
    MODEL_NAME: str = "gpt-4.1-nano"
    MAX_INPUT_LENGTH: int = 2000
    MAX_OUTPUT_LENGTH: int = 6000
    RATE_LIMIT_PER_SESSION: int = 60

    def get_database_url(self) -> str:
        return self.DATABASE_URL or self.SUPABASE_URL

    class Config:
        env_file = _ENV_FILE
        extra = "ignore"


settings = Settings()
