from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Smart Irrigation AI Platform"
    DATABASE_URL: str = "sqlite:///./agri.db"
    SECRET_KEY: str = "dev-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    SENSOR_API_KEY: str = "dev-sensor-key"
    FRONTEND_URL: str = "http://127.0.0.1:5173"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_STARTTLS: bool = True
    PASSWORD_RESET_DEV_MODE: bool = False

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()