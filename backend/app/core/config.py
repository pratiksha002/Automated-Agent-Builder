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

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()