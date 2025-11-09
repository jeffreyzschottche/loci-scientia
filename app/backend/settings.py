from pydantic import BaseModel


class Settings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    ws_path: str = "/ws"


def get_settings() -> "Settings":
    return Settings()


settings = get_settings()
