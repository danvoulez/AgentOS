from pydantic import BaseSettings

class Settings(BaseSettings):
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    SECRET_KEY: str
    DATABASE_URL: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
