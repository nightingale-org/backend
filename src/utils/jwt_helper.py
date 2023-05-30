import jwt

from src.config import app_config


class TokenInvalidException(Exception):
    def __init__(self, reason: str):
        self.reason = reason


# Create a PyJWT client using the Auth0 domain globally because this way it's cached
# TODO: fetching jwk keys should be done asynchronously
_jwks_client = jwt.PyJWKClient(
    f"https://{app_config.auth0_domain}/.well-known/jwks.json"
)


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
