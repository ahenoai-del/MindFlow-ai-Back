from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    BOT_TOKEN: str
    OPENAI_API_KEY: str = ""
    WEBAPP_URL: str = ""
    API_URL: str = ""
    ADMIN_IDS: Optional[List[int]] = None
    PROXY_URL: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
