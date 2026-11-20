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

    # ------------------------------------------------------------------ STT
    # Supported values: "mock" (no credentials needed) | "openai_whisper"
    STT_PROVIDER: str = "mock"
    # Required when STT_PROVIDER="openai_whisper"
    OPENAI_API_KEY: str = ""
    # Maximum audio upload size in megabytes (enforced before disk write)
    AUDIO_MAX_MB: int = 10
    # Maximum audio duration in seconds (enforced after file is accepted)
    AUDIO_MAX_SECONDS: int = 120
    # Directory for temporary audio files; "" means system temp dir
    AUDIO_TEMP_DIR: str = ""
    # Minutes after which unclaimed temp audio files are removed by the cleanup job
    AUDIO_RETENTION_MINUTES: int = 10

    # ------------------------------------------------------------------ TTS
    # Supported values: "mock" | "openai" | "google"
    TTS_PROVIDER: str = "mock"
    # Required when TTS_PROVIDER="openai"  (reuses OPENAI_API_KEY above)
    # Required when TTS_PROVIDER="google" — path to a service-account JSON key file,
    # or leave empty if GOOGLE_APPLICATION_CREDENTIALS env var is set system-wide.
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    # Maximum number of characters accepted as TTS input (applied to the speakable text)
    TTS_MAX_CHARS: int = 1000
    # Output audio format for TTS.  "mp3" works for all providers; "wav" for mock only.
    TTS_AUDIO_FORMAT: str = "mp3"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()