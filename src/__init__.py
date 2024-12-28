import os
from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)

    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    app.config.update(
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
        UPLOAD_FOLDER='/tmp', 
        AUTH0_DOMAIN=os.getenv('AUTH0_DOMAIN'),
        AUTH0_CLIENT_ID=os.getenv('AUTH0_CLIENT_ID'),
        AUTH0_AUDIENCE=os.getenv('AUTH0_AUDIENCE')
    )

    required_env_vars = [
        'AUTH0_DOMAIN',
        'AUTH0_CLIENT_ID',
        'AUTH0_AUDIENCE'
    ]

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    from .routes import init_routes
    init_routes(app)

    return app
