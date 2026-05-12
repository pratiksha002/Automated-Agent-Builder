from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BACKEND_URL: str = "http://localhost:8000"
    SECRET_KEY: str
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    RATE_LIMIT: str = "60/minute"
    APP_NAME: str = "Automated Agent Builder - Gateway"

    def get_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()