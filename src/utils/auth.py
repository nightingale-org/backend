from __future__ import annotations

from typing import Annotated
from typing import Any

import aiohttp
import jwt

from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
from jwt import PyJWK
from jwt import PyJWKSet
from jwt.api_jwt import decode_complete
from jwt.exceptions import PyJWKClientConnectionError
from jwt.exceptions import PyJWKClientError
from pydantic import BaseModel
from pydantic import Extra
from pydantic import Field
from pydantic import ValidationError

from src.config import app_config


token_auth_scheme = HTTPBearer()


class TokenInvalidError(Exception):
    def __init__(self, reason: str):
        self.reason = reason


class AsyncJWKClient(jwt.PyJWKClient):
    async def fetch_data(self) -> Any:
        jwk_set: Any = None
        timeout = aiohttp.ClientTimeout(total=self.timeout)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with await session.get(
                    self.uri, headers=self.headers
                ) as response:
                    jwk_set = await response.json()
        except aiohttp.ClientError as e:
            raise PyJWKClientConnectionError(
                f'Fail to fetch data from the url, err: "{e}"'
            ) from e
        else:
            return jwk_set
        finally:
            if self.jwk_set_cache is not None:
                self.jwk_set_cache.put(jwk_set)

    async def get_signing_key(self, kid: str) -> PyJWK:
        signing_keys = await self.get_signing_keys()
        signing_key = self.match_kid(signing_keys, kid)

        if not signing_key:
            # If no matching signing key from the jwk set, refresh the jwk set and try again.
            signing_keys = await self.get_signing_keys(refresh=True)
            signing_key = self.match_kid(signing_keys, kid)

            if not signing_key:
                raise PyJWKClientError(
                    f'Unable to find a signing key that matches: "{kid}"'
                )

        return signing_key

    async def get_signing_keys(self, refresh: bool = False) -> list[PyJWK]:
        jwk_set = await self.get_jwk_set(refresh)
        signing_keys = [
            jwk_set_key
            for jwk_set_key in jwk_set.keys
            if jwk_set_key.public_key_use in ["sig", None] and jwk_set_key.key_id
        ]

        if not signing_keys:
            raise PyJWKClientError(
                "The JWKS endpoint did not contain any signing keys"
            ) from None

        return signing_keys

    async def get_jwk_set(self, refresh: bool = False) -> PyJWKSet:
        data = None
        if self.jwk_set_cache is not None and not refresh:
            data = self.jwk_set_cache.get()

        if data is None:
            data = await self.fetch_data()

        if not isinstance(data, dict):
            raise PyJWKClientError(
                "The JWKS endpoint did not return a JSON object"
            ) from None

        return PyJWKSet.from_dict(data)

    async def get_signing_key_from_jwt(self, token: str) -> PyJWK:
        unverified = decode_complete(token, options={"verify_signature": False})
        header = unverified["header"]
        return await self.get_signing_key(header.get("kid"))


_async_jwks_client = AsyncJWKClient(
    f"https://{app_config.auth0_domain}/.well-known/jwks.json"
)


class UserCredentials(BaseModel):
    provider_account_id: str = Field(alias="sub")
    email: str

    class Config:
        extra = Extra.allow


async def validate_jwt_token(
    auth_credentials: Annotated[
        HTTPAuthorizationCredentials, Depends(token_auth_scheme)
    ]
):
    token = auth_credentials.credentials
    try:
        return await get_token_payload(token)
    except TokenInvalidError:
        raise HTTPException(status_code=401, detail="Invalid token") from None


def get_current_user_credentials(
    token_payload: Annotated[dict[str, str], Depends(validate_jwt_token)]
) -> UserCredentials:
    try:
        return UserCredentials(**token_payload)
    except ValidationError:
        raise HTTPException(status_code=401, detail="Invalid token") from None


async def get_token_payload(token: str) -> dict[str, str]:
    try:
        jwt_struct = await _async_jwks_client.get_signing_key_from_jwt(token)
    except jwt.PyJWKClientError as error:
        raise TokenInvalidError(str(error)) from error
    except jwt.DecodeError as error:
        raise TokenInvalidError(str(error)) from error

    try:
        payload = jwt.decode(
            token,
            jwt_struct.key,
            algorithms=["RS256"],
            audience=app_config.auth0_audience,
            issuer=app_config.auth0_jwt_issuer,
        )
    except Exception as e:
        raise TokenInvalidError(str(e)) from e

    return payload
