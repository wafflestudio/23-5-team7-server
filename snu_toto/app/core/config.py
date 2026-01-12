import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# 환경 변수로 설정된 환경
ENV = os.getenv("ENV", "local")
assert ENV in ("local", "test", "prod", "example")


class Settings(BaseSettings):
    @property
    def is_local(self) -> bool:
        return ENV == "local"
    
    @property
    def is_test(self) -> bool:
        return ENV == "test"

    @property
    def is_prod(self) -> bool:
        return ENV == "prod"

    @property
    def is_example(self) -> bool:
        return ENV == "example"

    @property
    def env_file(self) -> str:
        return str(BASE_DIR / f".env.{ENV}")

SETTINGS = Settings()


class DatabaseSettings(BaseSettings):
    dialect: str
    driver: str
    host: str
    port: int
    user: str
    password: str
    database: str
    
    @computed_field
    @property
    def url(self) -> str:
        return f"{self.dialect}+{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_prefix="DB_",
        env_file=SETTINGS.env_file,
        extra='ignore'
    )

DB_SETTINGS = DatabaseSettings()


class GoogleSettings(BaseSettings):
    CLIENT_ID: str
    CLIENT_SECRET: str
    REDIRECT_URI: str

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_prefix="GOOGLE_",
        env_file=SETTINGS.env_file,
        extra='ignore'
    )

GOOGLE_SETTINGS = GoogleSettings()
    

class RedisSettings(BaseSettings):
    URL: str

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_prefix="REDIS_",
        env_file=SETTINGS.env_file,
        extra='ignore'
    )

REDIS_SETTINGS = RedisSettings()


class EmailSettings(BaseSettings):
    HOST: str
    PORT: int
    USER: str
    PASSWORD: str

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_prefix="SMTP_",
        env_file=SETTINGS.env_file,
        extra='ignore'
    )

EMAIL_SETTINGS = EmailSettings()

class AuthSettings(BaseSettings):
    ACCESS_TOKEN_SECRET: str
    REFRESH_TOKEN_SECRET: str
    SHORT_SESSION_LIFESPAN: int = 15 # 15분
    LONG_SESSION_LIFESPAN: int = 24 * 60 # 24시간

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=SETTINGS.env_file,
        extra='ignore'
    )

AUTH_SETTINGS = AuthSettings()