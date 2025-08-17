from typing import List, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings
from decouple import config

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
        "http://localhost:8080"
    ]
    
    # Security
    SECRET_KEY: str = config("SECRET_KEY", default="your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # PostGIS
    POSTGIS_VERSION: str = "3.4"
    
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