from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    gemini_api_key: str
    upstash_vector_rest_url: str
    upstash_vector_rest_token: str
    upstash_redis_rest_url: str
    upstash_redis_rest_token: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
