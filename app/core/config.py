import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    KEITARO_API_KEY: str
    KEITARO_API_URL: str
    SQLALCHEMY_DATABASE_URI: str


settings = Settings()