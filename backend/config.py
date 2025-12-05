from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    
    # EVE Online SSO
    EVE_CLIENT_ID: str = ""
    EVE_CLIENT_SECRET: str = ""
    EVE_CALLBACK_URL: str = "http://localhost:8000/auth/callback"
    
    # LLM Provider Configuration
    LLM_PROVIDER: str = "openai"  # "openai" or "gemini"
    LLM_MODEL: str = "gpt-4-turbo-preview"  # Provider-specific model name
    
    # OpenAI API Key
    OPENAI_API_KEY: str = ""
    
    # Google Gemini API Key
    GEMINI_API_KEY: str = ""

    # Secret key for session/JWT
    SECRET_KEY: str = "change_this_in_production"

    class Config:
        env_file = ".env"

settings = Settings()
