from __future__ import annotations

import pathlib

from typing import Any
from typing import Final
from typing import Literal

from pydantic import Field
from pydantic import model_validator
from pydantic.networks import RedisDsn
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from src.utils import git


ENV_EXAMPLE_FILE_PATH = pathlib.Path(__file__).parent / ".env.example"
ENV_PROD_FILE_PATH = pathlib.Path(__file__).parent / ".env.prod"

TOKEN_STATE_KEY: Final[str] = "user"


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ENV_EXAMPLE_FILE_PATH, ENV_PROD_FILE_PATH), env_file_encoding="utf-8"
    )

    db_url: str = Field(validation_alias="DATABASE_URL")
    database_name: str = Field(validation_alias="DATABASE_NAME")

    redis_dsn: RedisDsn = Field(validation_alias="REDIS_DSN")

    openapi_title: str
    openapi_description: str
    version: str

    debug: bool = True
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG"

    auth0_domain: str = Field(validation_alias="AUTH0_DOMAIN")
    auth0_audience: str = Field(validation_alias="AUTH0_AUDIENCE")
    auth0_jwt_issuer: str

    s3_bucket_name: str
    s3_access_key: str
    s3_secret_key: str
    s3_region_name: str

    test_db_name: str = "test_database"

    @model_validator(mode="before")
    @classmethod
    def set_version_from_git(cls, data: dict[str, Any]) -> dict[str, Any]:
        if "version" not in data:
            data["version"] = git.get_revision_hash()

        auth0_domain = data["AUTH0_DOMAIN"]
        data["auth0_jwt_issuer"] = f"https://{auth0_domain}/"

        return data


app_config = AppConfig()
