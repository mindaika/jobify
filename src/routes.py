import os
from typing import Tuple, Dict, Any, Union
from datetime import datetime
import requests
import psycopg2
from flask import jsonify, request, Response
from werkzeug.utils import secure_filename
from .auth import AuthError, requires_auth
from .utils import extract_text_from_file, get_anthropic_client

JsonResponse = Union[Response, Tuple[Response, int]]

DATABASE_URL = os.environ.get('DATABASE_URL')

def _get_db_conn():
    """Get a database connection."""
    return psycopg2.connect(DATABASE_URL)

def _init_hit_counter():
    """Create the website schema and visitors table if they don't exist."""
    with _get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS website")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS website.visitors (
                    id SERIAL PRIMARY KEY,
                    visitor_id VARCHAR(36) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

def get_hit_count() -> int:
    """Get the unique visitor count."""
    with _get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM website.visitors")
            return cur.fetchone()[0]

def register_visitor(visitor_id: str) -> int:
    """Register a visitor and return the total count. Ignores duplicates."""
    with _get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO website.visitors (visitor_id) VALUES (%s) ON CONFLICT DO NOTHING",
                (visitor_id,)
            )
            cur.execute("SELECT COUNT(*) FROM website.visitors")
            return cur.fetchone()[0]

def allowed_file(filename: str) -> bool:
    """
    Check allowed file extensions.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        bool: Whether the file extension is allowed
    """
    allowed_extensions = {'pdf', 'md', 'txt'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def init_routes(app):
    @app.route('/api/status')
    def api_status() -> JsonResponse:
        """Health check endpoint."""
        return jsonify({"status": "ok"})

    @app.route('/api/process_resume', methods=['POST', 'OPTIONS'])
    @requires_auth
    def process_resume(current_user: str) -> JsonResponse:
        """
        Process resume with authentication.
        
        Args:
            current_user: User ID from JWT token
            
        Returns:
            JSON response with processed resume or error
        """
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            return response

        try:
            # File validation
            if 'resume' not in request.files:
                return jsonify({
                    'success': False, 
                    'error': 'No resume file uploaded'
                }), 400

            file = request.files['resume']
            if file.filename == '':
                return jsonify({
                    'success': False, 
                    'error': 'No file selected'
                }), 400

            if not allowed_file(file.filename):
                return jsonify({
                    'success': False,
                    'error': 'Invalid file type. Supported types: PDF, Markdown, Text'
                }), 400

            # Form data validation
            job_description = request.form.get('job_description', '').strip()
            improvement_prompt = request.form.get('improvement_prompt', '').strip()

            if not job_description:
                return jsonify({
                    'success': False, 
                    'error': 'Job description is required'
                }), 400

            # Process file
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                resume_text = extract_text_from_file(filepath)
            finally:
                # Ensure file cleanup
                if os.path.exists(filepath):
                    os.remove(filepath)

            # Process with Claude
            try:
                processor = get_anthropic_client()
                result = processor.process_document(
                    document_text=resume_text,
                    job_description=job_description,
                    improvement_prompt=improvement_prompt
                )
                
                return jsonify({
                    'success': True,
                    'improved_resume': result
                })
            
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Error processing resume: {str(e)}'
                }), 500

        except AuthError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), e.status_code
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # Error handlers
    @app.errorhandler(AuthError)
    def handle_auth_error(ex: AuthError) -> JsonResponse:
        """Handle authentication errors."""
        response = jsonify({
            "success": False,
            "error": ex.error
        })
        return response, ex.status_code

    @app.route('/api/footer-data')
    def get_footer_data() -> JsonResponse:
        """Fetch year data from external API or fallback to current year."""
        try:
            response = requests.get('https://getfullyear.com/api/year', timeout=5)
            if response.ok:
                return jsonify(response.json())
        except requests.exceptions.Timeout as e:
            app.logger.warning(f"Timeout fetching year data: {str(e)}")
        except Exception as e:
            app.logger.error(f"Error fetching year data: {str(e)}")

        # Fallback to current year if API fails
        return jsonify({
            'year': datetime.now().year,
            'sponsored_by': 'None'
        })

    @app.route('/api/hit-counter', methods=['GET'])
    def get_hit_counter() -> JsonResponse:
        """Get the current hit count."""
        try:
            count = get_hit_count()
            return jsonify({'count': count})
        except Exception as e:
            app.logger.error(f"Error getting hit count: {str(e)}")
            return jsonify({'count': 0}), 500

    @app.route('/api/hit-counter/increment', methods=['POST'])
    def increment_hit_counter() -> JsonResponse:
        """Register a visitor and return the total unique visitor count."""
        try:
            body = request.get_json(silent=True) or {}
            visitor_id = body.get('visitor_id', '')
            if not visitor_id:
                return jsonify({'error': 'visitor_id required'}), 400
            count = register_visitor(visitor_id)
            return jsonify({'count': count})
        except Exception as e:
            app.logger.error(f"Error incrementing hit count: {str(e)}")
            return jsonify({'error': 'Failed to increment counter'}), 500