from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Automated Agent Builder"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # Auth
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ── Groq API Keys (one per model) ─────────────────────────────────────────
    GROQ_KEY_LLAMA_70B: str
    GROQ_KEY_LLAMA_8B: str
    GROQ_KEY_MIXTRAL: str
    GROQ_KEY_GEMMA: str

    # ── Ollama ────────────────────────────────────────────────────────────────
    # Base URL of the local Ollama server.
    # Default: http://localhost:11434 (standard Ollama install)
    # Override in .env: OLLAMA_BASE_URL=http://192.168.1.10:11434
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Whether Ollama is available in this deployment.
    # Set to false in cloud environments where Ollama isn't running.
    OLLAMA_ENABLED: bool = True

    # Timeout in seconds for Ollama HTTP calls (local models can be slow to start)
    OLLAMA_TIMEOUT: int = 120

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # ── Rate limiting ─────────────────────────────────────────────────────────
    CHAT_RATE_LIMIT: str = "20/minute"

    # Encryption (for api_keys table)
    ENCRYPTION_MASTER_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()