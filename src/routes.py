import os
from flask import jsonify, send_from_directory, request
from .auth import token_required

def init_routes(app):
    @app.route('/api/status')
    def api_status():
        """Health check endpoint"""
        return jsonify({"status": "okeydokey"})
    
    @app.route('/api/config')
    def get_config():
        return jsonify({
            'auth0Domain': os.getenv('AUTH0_DOMAIN'),
            'auth0ClientId': os.getenv('AUTH0_CLIENT_ID'),
            'auth0Audience': os.getenv('AUTH0_AUDIENCE')
        })

    @app.route('/api/process_resume', methods=['POST', 'OPTIONS'])
    @token_required
    def process_resume(current_user):
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            return response
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
        pass
    
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
