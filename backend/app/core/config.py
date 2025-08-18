from typing import List, Union, Optional
from pydantic import AnyHttpUrl, validator, EmailStr
from pydantic_settings import BaseSettings
from decouple import config
import secrets

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Parking Management System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = config("DATABASE_URL", default="postgresql+asyncpg://postgres:password@localhost:5432/parking_db")
    
    # Redis
    REDIS_URL: str = config("REDIS_URL", default="redis://localhost:6379")
    
    # Elasticsearch
    ELASTICSEARCH_URL: str = config("ELASTICSEARCH_URL", default="http://localhost:9200")
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = config("KAFKA_BOOTSTRAP_SERVERS", default="localhost:9092")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",
        "https://localhost:3000",
        "https://localhost:8000",
        "https://localhost:8080"
    ]
    
    # Security & Authentication
    SECRET_KEY: str = config("SECRET_KEY", default=secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = config("ACCESS_TOKEN_EXPIRE_MINUTES", default=30, cast=int)
    REFRESH_TOKEN_EXPIRE_MINUTES: int = config("REFRESH_TOKEN_EXPIRE_MINUTES", default=7 * 24 * 60, cast=int)  # 7 days
    
    # Password Security
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = config("RATE_LIMIT_PER_MINUTE", default=60, cast=int)
    RATE_LIMIT_BURST: int = config("RATE_LIMIT_BURST", default=10, cast=int)
    
    # OAuth Configuration
    GOOGLE_CLIENT_ID: Optional[str] = config("GOOGLE_CLIENT_ID", default=None)
    GOOGLE_CLIENT_SECRET: Optional[str] = config("GOOGLE_CLIENT_SECRET", default=None)
    GITHUB_CLIENT_ID: Optional[str] = config("GITHUB_CLIENT_ID", default=None)
    GITHUB_CLIENT_SECRET: Optional[str] = config("GITHUB_CLIENT_SECRET", default=None)
    
    # Email Configuration
    SMTP_TLS: bool = config("SMTP_TLS", default=True, cast=bool)
    SMTP_PORT: Optional[int] = config("SMTP_PORT", default=587, cast=int)
    SMTP_HOST: Optional[str] = config("SMTP_HOST", default=None)
    SMTP_USER: Optional[str] = config("SMTP_USER", default=None)
    SMTP_PASSWORD: Optional[str] = config("SMTP_PASSWORD", default=None)
    EMAILS_FROM_EMAIL: Optional[EmailStr] = config("EMAILS_FROM_EMAIL", default=None)
    EMAILS_FROM_NAME: Optional[str] = config("EMAILS_FROM_NAME", default=None)
    
    # SSL/TLS Configuration
    SSL_CERTIFICATE_PATH: Optional[str] = config("SSL_CERTIFICATE_PATH", default=None)
    SSL_PRIVATE_KEY_PATH: Optional[str] = config("SSL_PRIVATE_KEY_PATH", default=None)
    USE_SSL: bool = config("USE_SSL", default=False, cast=bool)
    
    # Security Headers
    ENABLE_SECURITY_HEADERS: bool = True
    
    # API Documentation
    OPENAPI_URL: str = "/openapi.json"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    
    # PostGIS
    POSTGIS_VERSION: str = "3.4"
    
    # Environment
    ENVIRONMENT: str = config("ENVIRONMENT", default="development")
    DEBUG: bool = config("DEBUG", default=True, cast=bool)
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        case_sensitive = True

settings = Settings()