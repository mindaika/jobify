from os import environ
from functools import wraps
import json
from urllib.request import urlopen
from jose import jwt
from flask import request, jsonify

class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


def get_token_auth_header():
    """Obtains the Access Token from the Authorization Header"""
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise AuthError("Authorization header is missing", 401)

    parts = auth.split()
    if parts[0].lower() != "bearer":
        raise AuthError("Authorization header must start with Bearer", 401)
    elif len(parts) == 1:
        raise AuthError("Token not found", 401)
    elif len(parts) > 2:
        raise AuthError("Authorization header must be Bearer token", 401)

    token = parts[1]
    return token


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_auth_header()

        # Fetch JWKS
        jsonurl = urlopen(f'https://{environ["AUTH0_DOMAIN"]}/.well-known/jwks.json')
        jwks = json.loads(jsonurl.read())

        # Decode token
        try:
            unverified_header = jwt.get_unverified_header(token)
        except jwt.JWTError:
            raise AuthError("Invalid header. Token malformed.", 401)

        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
        if not rsa_key:
            raise AuthError("Unable to find appropriate key", 401)

        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                audience=environ["AUTH0_AUDIENCE"],
                issuer=f'https://{environ["AUTH0_DOMAIN"]}/'
            )
        except jwt.ExpiredSignatureError:
            raise AuthError("Token is expired", 401)
        except jwt.JWTClaimsError:
            raise AuthError("Invalid claims", 401)
        except Exception:
            raise AuthError("Unable to parse authentication token", 401)

        # Pass `current_user` to the wrapped function
        current_user = payload.get("sub")
        return f(current_user=current_user, *args, **kwargs)

    return decorated
