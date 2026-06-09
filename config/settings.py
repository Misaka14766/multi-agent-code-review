"""Application settings loaded from environment variables and .env file."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Application ---
    APP_NAME: str = "Multi-Agent Code Review"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- LLM ---
    LLM_PROVIDER: str = "mock"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096
    LLM_TIMEOUT_SECONDS: int = 60

    # --- Embedding ---
    EMBEDDING_PROVIDER: str = "mock"

    # --- Orchestrator ---
    AGENT_TIMEOUT_SECONDS: int = 30
    MAX_REPAIR_ATTEMPTS: int = 3
    CIRCUIT_BREAKER_THRESHOLD: int = 2

    # --- Vector Store ---
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    CHROMA_COLLECTION_NAME: str = "code_review_knowledge"

    # --- GitHub Integration ---
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_TOKEN: str = ""
    GITHUB_CHECKS_ENABLED: bool = False

    # --- Tools ---
    SEMGREP_ENABLED: bool = True
    PYLINT_ENABLED: bool = True
    SANDBOX_ENABLED: bool = False

    # --- Paths ---
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    PROMPTS_DIR: Path = PROJECT_ROOT / "prompts"
    KNOWLEDGE_DATA_DIR: Path = PROJECT_ROOT / "knowledge_data"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
