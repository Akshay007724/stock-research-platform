from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    groq_api_key: str = ""
    finnhub_api_key: str = ""
    fmp_api_key: str = ""
    alpha_vantage_key: str = ""
    polygon_api_key: str = ""
    news_api_key: str = ""
    database_url: str = "postgresql+asyncpg://srp:srp@postgres:5432/srp"
    redis_url: str = "redis://redis:6379/0"
    qdrant_host: str = "qdrant"
    # LLM provider: "groq" (default, open-source Llama via Groq API)
    #               "openai" (OpenAI GPT models)
    llm_provider: str = "groq"
    openai_model: str = "gpt-4o-mini"
    groq_model: str = "llama-3.3-70b-versatile"
    log_level: str = "info"


settings = Settings()
