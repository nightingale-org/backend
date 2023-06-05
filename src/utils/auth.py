from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Extra, Field, ValidationError

from src.config import app_config

token_auth_scheme = HTTPBearer()


class TokenInvalidException(Exception):
    def __init__(self, reason: str):
        self.reason = reason


# Create a PyJWT client using the Auth0 domain globally because this way it's cached
# TODO: fetching jwk keys should be done asynchronously
_jwks_client = jwt.PyJWKClient(
    f"https://{app_config.auth0_domain}/.well-known/jwks.json"
)


class UserCredentials(BaseModel):
    provider_account_id: str = Field(alias="sub")
    email: str

    class Config:
        extra = Extra.allow


def validate_jwt_token(
    auth_credentials: Annotated[
        HTTPAuthorizationCredentials, Depends(token_auth_scheme)
    ]
):
    token = auth_credentials.credentials
    try:
        return get_token_payload(token)
    except TokenInvalidException:
        raise HTTPException(status_code=401, detail="Invalid token") from None


def get_current_user_credentials(
    token_payload: Annotated[dict[str, str], Depends(validate_jwt_token)]
) -> UserCredentials:
    try:
        return UserCredentials(**token_payload)
    except ValidationError:
        raise HTTPException(status_code=401, detail="Invalid token") from None


def get_token_payload(token: str) -> dict[str, str]:
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token).key
    except jwt.PyJWKClientError as error:
        raise TokenInvalidException(str(error)) from error
    except jwt.DecodeError as error:
        raise TokenInvalidException(str(error)) from error

    try:
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=app_config.auth0_audience,
            issuer=app_config.auth0_jwt_issuer,
        )
    except Exception as e:
        raise TokenInvalidException(str(e)) from e

    return payload
