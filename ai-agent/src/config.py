"""
Configuration settings for the AI Agent service
"""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    env: str = "development"
    port: int = 8000
    debug: bool = False

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vibber"
    redis_url: str = "redis://localhost:6379"

    # Message Queue
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    # AI Models
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    default_model: str = "claude-3-5-sonnet-20241022"
    embedding_model: str = "text-embedding-3-large"

    # Vector Database
    pinecone_api_key: str = ""
    pinecone_index: str = "vibber-agents"
    pinecone_environment: str = "us-east-1"

    # Agent Configuration
    default_confidence_threshold: int = 70
    max_context_tokens: int = 100000
    max_output_tokens: int = 4096

    # Rate Limiting
    max_requests_per_minute: int = 60
    max_tokens_per_minute: int = 100000

    # Integration credentials (for testing)
    slack_bot_token: str = ""
    github_token: str = ""
    jira_api_token: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
