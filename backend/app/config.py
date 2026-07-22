from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    # usados apenas para criar o usuário admin inicial no primeiro start (banco vazio)
    admin_username: str
    admin_password: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    base_url: str = "http://localhost:8080"
    cookie_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
