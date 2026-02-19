from flask import Flask
from flask_cors import CORS
from .routes import init_routes, _init_hit_counter

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
        UPLOAD_FOLDER='/tmp'
    )

    init_routes(app)
    _init_hit_counter()

    return app
