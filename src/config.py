import pathlib
from typing import Any, Final, Literal

from pydantic import BaseSettings, Field, root_validator
from pydantic.networks import MongoDsn

from src.utils import git

ENV_EXAMPLE_FILE_PATH = pathlib.Path(__file__).parent / ".env.example"
ENV_PROD_FILE_PATH = pathlib.Path(__file__).parent / ".env.prod"

TOKEN_STATE_KEY: Final[str] = "user"


class AppConfig(BaseSettings):
    db_url: MongoDsn = Field(env="DATABASE_URL")
    database_name: str = Field(env="DATABASE_NAME")

    openapi_title: str
    openapi_description: str
    version: str

    debug: bool = True
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG"

    auth0_domain: str = Field(env="AUTH0_DOMAIN")
    auth0_audience: str = Field(env="AUTH0_AUDIENCE")
    auth0_jwt_issuer: str

    @root_validator(pre=True)
    def set_version_from_git(cls, values: dict[str, Any]) -> dict[str, Any]:
        if "version" not in values:
            values["version"] = git.get_revision_hash()

        auth0_domain = values["auth0_domain"]
        values["auth0_jwt_issuer"] = f"https://{auth0_domain}/"

        return values

    class Config:
        env_file = (ENV_EXAMPLE_FILE_PATH, ENV_PROD_FILE_PATH)
        env_file_encoding = "utf-8"


app_config = AppConfig()
