from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "随便聊"
    app_version: str = "1.0.0"
    app_host: str = "0.0.0.0"
    app_port: int = 5000
    debug: bool = True

    # MongoDB 配置
    mongodb_uri: str = "mongodb://mongodb:27017"
    mongodb_db_name: str = "anonymous_chat"

    # Redis 配置
    redis_uri: str = "redis://redis:6379"
    redis_db: int = 0

    # JWT 配置
    jwt_secret_key: str = "your-super-secret-jwt-key-change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # 文件上传配置
    upload_dir: str = "./public/uploads"
    max_upload_size: int = 10485760

    # 环境
    node_env: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
