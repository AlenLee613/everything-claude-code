from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    USE_FAKEREDIS: bool = False

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
