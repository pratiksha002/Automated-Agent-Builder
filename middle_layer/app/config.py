from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BACKEND_URL: str = "https://automated-agent-builder.onrender.com"
    SECRET_KEY: str
    ALLOWED_ORIGINS: str = "https://automated-agent-builder.vercel.app/, http://localhost:8000, http://localhost:3000, http://127.0.0.1:5500"
    RATE_LIMIT: str = "60/minute"
    APP_NAME: str = "Automated Agent Builder - Gateway"

    def get_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()