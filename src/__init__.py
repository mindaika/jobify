from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from .utils import (
    allowed_file, 
    extract_text_from_file, 
    get_anthropic_client
)

def create_app():
    app = Flask(__name__,
                static_folder='static',
                static_url_path='')
    
    # Enable CORS
    CORS(app)
    
    app.config.update(
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
        UPLOAD_FOLDER='/tmp',                 # Temporary storage for uploads
    )

    @app.route('/')
    def serve_static():
        """Serve the static index.html file"""
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/<path:path>')
    def serve_static_path(path):
        """Serve static files or return index.html for client-side routing"""
        if os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/api/status')
    def api_status():
        """Health check endpoint"""
        return jsonify({"status": "okeydokey"})

    @app.route('/api/process_resume', methods=['POST'])
    def process_resume():
        """Process resume and return improved version"""
        try:
            # Validate file upload
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

            # Get form data
            job_description = request.form.get('job_description', '')
            improvement_prompt = request.form.get('improvement_prompt', '')

            if not job_description:
                return jsonify({
                    'success': False,
                    'error': 'Job description is required'
                }), 400

            # Save and process file
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                # Extract text from uploaded file
                resume_text = extract_text_from_file(filepath)
            finally:
                # Clean up temporary file
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

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    return app