from os import environ
from flask import request
from functools import wraps
import json
from urllib.request import urlopen
from jose import jwt
from typing import Callable, Any

class AuthError(Exception):
    """Custom exception for authentication errors."""
    def __init__(self, error: str, status_code: int):
        self.error = error
        self.status_code = status_code

def get_token_auth_header() -> str:
    """
    Obtains the Access Token from the Authorization Header
    
    Returns:
        str: The token part of the authorization header
        
    Raises:
        AuthError: If the header is malformed or missing
    """
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

def requires_auth(f: Callable) -> Callable:
    """
    Decorator to protect routes with JWT authentication
    
    Args:
        f: Function to wrap
        
    Returns:
        Callable: Decorated function
    """
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        token = get_token_auth_header()
        domain = environ["AUTH0_DOMAIN"]
        audience = environ["AUTH0_AUDIENCE"]

        try:
            # Fetch JWKS
            jsonurl = urlopen(f'https://{domain}/.well-known/jwks.json')
            jwks = json.loads(jsonurl.read())
            
            # Get unverified header
            try:
                unverified_header = jwt.get_unverified_header(token)
            except jwt.JWTError:
                raise AuthError("Invalid header. Token malformed.", 401)

            # Find matching key
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
                    break
                    
            if not rsa_key:
                raise AuthError("Unable to find appropriate key", 401)

            # Decode and validate token
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                audience=audience,
                issuer=f'https://{domain}/'
            )

            # Pass current_user to wrapped function
            current_user = payload.get("sub")
            return f(current_user=current_user, *args, **kwargs)

        except jwt.ExpiredSignatureError:
            raise AuthError("Token is expired", 401)
        except jwt.JWTClaimsError:
            raise AuthError("Invalid claims", 401)
        except Exception:
            raise AuthError("Unable to parse authentication token", 401)

    return decorated