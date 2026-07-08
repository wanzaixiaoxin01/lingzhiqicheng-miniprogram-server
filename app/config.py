from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "lingzhi-qicheng-api"
    database_url: str = "postgresql+psycopg://lingzhi:lingzhi_password@127.0.0.1:5432/lingzhi_qicheng"
    secret_key: str = "dev-only-secret"
    upload_dir: str = "./uploads"
    miniprogram_app_id: str = ""
    miniprogram_app_secret: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
