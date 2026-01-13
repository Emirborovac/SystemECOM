from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "SystemECOM"
    env: str = "dev"

    api_v1_prefix: str = "/api/v1"

    # Security
    jwt_secret: str = "change_me"
    access_token_expires_minutes: int = 30
    refresh_token_expires_days: int = 14

    # Infra (phase 1)
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/systemecom"
    redis_url: str = "redis://localhost:6379/0"

    # CORS (frontend dev)
    cors_origins: str = "http://localhost:3000"

    # Frontend base URL for links in emails (dev)
    frontend_base_url: str = "http://localhost:3000"

    # Notifications (email) toggles
    notify_inbound_received_email: bool = False
    notify_outbound_dispatched_email: bool = False
    notify_invoice_issued_email: bool = True

    # File storage
    file_storage_provider: str = "LOCAL"  # LOCAL / S3 / MINIO
    file_storage_root: str = ".storage"  # used for LOCAL

    # S3 / MinIO
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_bucket: str | None = None


settings = Settings()




