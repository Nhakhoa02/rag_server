from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    # Database settings
    mongodb_uri: str = "mongodb://admin:password123@localhost:27018/rag_db?authSource=admin"
    redis_url: str = "redis://localhost:6379/0"
    
    # Vector database settings
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "rag_documents"
    
    # LLM settings
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "gemini-pro"  # Default to Gemini
    llm_provider: str = "gemini"   # gemini, openai, or ollama
    
    # File processing settings
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    upload_dir: str = "./uploads"
    supported_formats: List[str] = ["pdf", "docx", "xlsx", "csv", "txt", "png", "jpg", "jpeg"]
    
    # RAG settings
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_model: str = "all-MiniLM-L6-v2"
    top_k: int = 5
    
    # Security settings
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Logging settings
    log_level: str = "INFO"
    log_file: str = "./logs/rag_server.log"
    
    # Monitoring settings
    enable_metrics: bool = True
    metrics_port: int = 8001
    
    # Offline mode for development
    offline_mode: bool = False
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }

# Create settings instance
settings = Settings()

# Environment-specific overrides
mongodb_uri_env = os.getenv("MONGODB_URI")
if mongodb_uri_env:
    settings.mongodb_uri = mongodb_uri_env

redis_url_env = os.getenv("REDIS_URL")
if redis_url_env:
    settings.redis_url = redis_url_env

qdrant_url_env = os.getenv("QDRANT_URL")
if qdrant_url_env:
    settings.qdrant_url = qdrant_url_env

qdrant_collection_env = os.getenv("QDRANT_COLLECTION_NAME")
if qdrant_collection_env:
    settings.qdrant_collection_name = qdrant_collection_env

gemini_key_env = os.getenv("GEMINI_API_KEY")
if gemini_key_env:
    settings.gemini_api_key = gemini_key_env

ollama_url_env = os.getenv("OLLAMA_BASE_URL")
if ollama_url_env:
    settings.ollama_base_url = ollama_url_env

llm_provider_env = os.getenv("LLM_PROVIDER")
if llm_provider_env:
    settings.llm_provider = llm_provider_env 