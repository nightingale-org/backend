from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.utils.jwt_helper import TokenInvalidException, get_token_payload

token_auth_scheme = HTTPBearer()


def protected_route(
    auth_credentials: Annotated[
        HTTPAuthorizationCredentials, Depends(token_auth_scheme)
    ]
):
    token = auth_credentials.credentials
    try:
        return get_token_payload(token)
    except TokenInvalidException:
        raise HTTPException(status_code=401, detail="Invalid token") from None
