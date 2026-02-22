import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Mental Health Tracker"
    PROJECT_VERSION: str = "1.0.0"

    # Construct DATABASE_URL for SQLite
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./mental_health.db"
    )

    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")

settings = Settings()
