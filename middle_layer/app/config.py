from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # The backend FastAPI app URL
    BACKEND_URL: str = "http://localhost:8000"

    # Must match the backend's SECRET_KEY exactly — used to verify JWTs
    SECRET_KEY: str

    # Origins the frontend is allowed to call from
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # Rate limiting — requests per minute per user
    RATE_LIMIT: str = "60/minute"

    APP_NAME: str = "Automated Agent Builder - Gateway"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()