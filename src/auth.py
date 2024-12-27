from functools import wraps
import json
from flask import request, jsonify, current_app
from jose import jwt
from urllib.request import urlopen

def get_auth_config():
    return {
        'domain': current_app.config['AUTH0_DOMAIN'],
        'audience': current_app.config['AUTH0_AUDIENCE'],
        'algorithms': ["RS256"]
    }

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_config = get_auth_config()
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Token is missing'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
            
        try:
            jsonurl = urlopen(f"https://{auth_config['domain']}/.well-known/jwks.json")
            jwks = json.loads(jsonurl.read())
            unverified_header = jwt.get_unverified_header(token)
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
                    
            if rsa_key:
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=auth_config['algorithms'],
                    audience=auth_config['audience'],
                    issuer=f"https://{auth_config['domain']}/"
                )
                return f(payload, *args, **kwargs)
            
        except Exception as e:
            return jsonify({'error': f'Token is invalid: {str(e)}'}), 401
            
        return jsonify({'error': 'Unable to find appropriate key'}), 401
    
    return decorated