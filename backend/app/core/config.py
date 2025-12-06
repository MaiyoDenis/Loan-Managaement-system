from pydantic_settings import BaseSettings
from pydantic import field_validator, AnyHttpUrl
from typing import List, Union, Any

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    SERVER_NAME: str = "Kim Loans Management System"
    SERVER_HOST: str = "http://localhost"
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",  # React dev server
        "http://127.0.0.1:3000",
        "http://localhost:8080",
    ]

    # Database Configuration
    DATABASE_URL: str = "postgresql://loan_user:loan_password@localhost/loan_management_db"

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"

    # Security Settings
    PASSWORD_MIN_LENGTH: int = 8
    DEFAULT_ADMIN_EMAIL: str = "admin@kimlonans.com"
    DEFAULT_ADMIN_PASSWORD: str = "KimLoans2024!"

    # Business Settings
    DEFAULT_REGISTRATION_FEE: float = 800.00
    DEFAULT_LOAN_LIMIT_MULTIPLIER: int = 4
    DEFAULT_GRACE_PERIOD_MINUTES: int = 60
    DEFAULT_REORDER_POINT: int = 5
    DEFAULT_CRITICAL_POINT: int = 2

    # External API Settings (for future M-Pesa integration)
    MPESA_CONSUMER_KEY: str = ""
    MPESA_CONSUMER_SECRET: str = ""
    MPESA_SHORTCODE: str = ""

    # SMS Gateway Settings
    SMS_API_KEY: str = ""
    SMS_API_URL: str = ""

    # Email Settings
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    @field_validator("BACKEND_CORS_ORIGINS")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        env_file = ".env"


settings = Settings()
