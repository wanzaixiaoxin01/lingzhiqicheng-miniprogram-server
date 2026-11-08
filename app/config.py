from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "lingzhi-qicheng-api"
    database_url: str = "postgresql+psycopg://lingzhi:lingzhi_password@127.0.0.1:5432/lingzhi_qicheng"
    secret_key: str = "dev-only-secret"
    upload_dir: str = "./uploads"
    max_material_size: int = 100 * 1024 * 1024
    miniprogram_app_id: str = ""
    miniprogram_app_secret: str = ""
    public_base_url: str = ""
    admin_username: str = "admin"
    admin_password: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
