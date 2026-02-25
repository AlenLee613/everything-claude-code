from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    USE_FAKEREDIS: bool = False
    
    # Storage Configuration
    STORAGE_TYPE: str = "local"  # Options: "redis", "local"
    LOCAL_STORAGE_PATH: str = "data/storage.db"
    
    # Security
    TRUSTED_PROXIES: str = ""  # Comma separated list of trusted proxy IPs

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
