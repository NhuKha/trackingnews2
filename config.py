from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Stock Signal"
    database_url: str = "sqlite:///./stock_signal.db"
    sec_user_agent: str = "StockSignal/0.3 your-email@example.com"
    sec_timeout_seconds: float = 15.0

    x_bearer_token: str | None = None
    newsapi_key: str | None = None
    finnhub_api_key: str | None = None

    openai_api_key: str | None = None
    openai_model: str = "gpt-6-luna"

    # Personal-app access control. Leave blank for local development with no login.
    app_password: str | None = None
    app_secret: str = "change-me-before-deploying"
    cookie_secure: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
