from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field
from enum import Enum
from dotenv import find_dotenv, load_dotenv
import google.generativeai as genai
import logging
from typing import Any
load_dotenv(find_dotenv(".env"))


class AppConfig(BaseSettings):
    PROJECT_NAME: str = 'vm-agent'
    PROJECT_DESCRIPTION: str = "vincilium - py-agent"


class PostgresSQLConnectionConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_")
    HOST: str = "local"
    USER: str = "vincilium"
    PASSWORD: str = "vincilium"
    DATABASE: str = "blockreconsit"
    PORT: str = "5452"


class ApiKeyConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="API_KEY_")
    GOOGLE_API_KEY: str = Field(default="")


class LLMModel(str,Enum):
    GEMINI_FLASH_002:str = "gemini-1.5-flash-002"

class FetchToken(BaseSettings):
    token: str
    model_config = {
        "env_prefix": "ACCESS_",
    }


app_config = AppConfig()
apikey_config = ApiKeyConfig()
logging.info(f"--->api key : {apikey_config.GOOGLE_API_KEY}")
pg_config = PostgresSQLConnectionConfig()
access_token = FetchToken()
logging.info(f"--->access token : {access_token.token}")

