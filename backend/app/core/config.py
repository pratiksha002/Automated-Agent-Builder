from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Automated Agent Builder"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str  # e.g. postgresql://user:pass@localhost:5432/agentbuilder

    # Auth
    SECRET_KEY: str           # For JWT signing
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Groq API Keys (one per model, loaded from .env)
    GROQ_KEY_LLAMA_70B: str
    GROQ_KEY_LLAMA_8B: str
    GROQ_KEY_MIXTRAL: str
    GROQ_KEY_GEMMA: str

    # Encryption (for api_keys table if used)
    ENCRYPTION_MASTER_KEY: str = ""

    # ── Step 5.4 — CORS ───────────────────────────────────────────────────────
    # Comma-separated list of allowed frontend origins.
    # Example in .env:
    #   CORS_ORIGINS=http://localhost:5173,https://yourapp.vercel.app
    # Defaults to localhost Vite dev server so local dev works out of the box.
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # ── Step 5.3 — Rate Limiting ──────────────────────────────────────────────
    # Controls how many chat requests a single IP can make per minute.
    # Format follows slowapi/limits syntax: "N/minute", "N/hour", etc.
    # Override in .env: CHAT_RATE_LIMIT=10/minute
    CHAT_RATE_LIMIT: str = "20/minute"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()