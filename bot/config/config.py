from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    MULTI_TAPPERS: int = 5
    BOT_NAME: str = "notpixel"

    REF_LINK: str = "https://t.me/notpixel/app?startapp=f5440629352"
    CHANNEL_REF_LINK: str = "https://web.telegram.org/k/#@lhsdevlink"
    GPM_API_URL: str = "http://127.0.0.1:19995"

    X3POINTS: bool = True
    AUTO_UPGRADE_PAINT_REWARD: bool = True
    AUTO_UPGRADE_RECHARGE_SPEED:bool = True
    AUTO_UPGRADE_RECHARGE_ENERGY:bool = True
    AUTO_TASK: bool = True

    PROXY_CHECK_SSL: bool = True

    CHECK_BUTTON_LAUNCH_GAME: bool = False
    TIME_OUT_CHECK_BUTTON_LAUNCH_GAME: int = 10

    DELAY_EACH_ACCOUNT: list[int] = [10,15]
    DELAY_BEFORE_TAPPER: list[int] = [1,10]
    DELAY_AFTER_DONE_TAPPER: list[int] = [1200,1756]

    USE_PROXY_FROM_FILE: bool = False


settings = Settings()

