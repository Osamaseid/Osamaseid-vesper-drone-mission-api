import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Vesper Drone Light-Painting API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    database_url: str = "sqlite:///./vesper.db"
    
    host: str = "0.0.0.0"
    port: int = 8080
    reload: bool = False
    
    log_level: str = "INFO"
    
    cors_origins: list = ["*"]
    
    max_exposure_count: int = 10000
    max_speed_ms: float = 5.0
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
