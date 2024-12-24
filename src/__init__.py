from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from .utils import allowed_file, extract_text_from_pdf, get_anthropic_client
import httpx


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
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/<path:path>')
    def serve_static_path(path):
        if os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/api/status')
    def api_status():
        return jsonify({"status": "ok"})
    
    @app.route('/api/debug21556')
    def debug():
        from anthropic import Anthropic
        api_key = os.getenv('ANTHROPIC_API_KEY')
        
        http_client = httpx.Client(proxies=None)  # Override proxy settings explicitly
        client = Anthropic(api_key=api_key, http_client=http_client)

        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=100,
            temperature=0.7,
            messages=[{"role": "user", "content": "Test message"}],
        )
        print(response)
        
        
        return jsonify({"status": "ok"})

    @app.route('/api/process_resume', methods=['POST'])
    def process_resume():
        try:
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
                    'error': 'Invalid file type. Please upload a PDF.'
                }), 400

            job_description = request.form.get('job_description', '')
            improvement_prompt = request.form.get('improvement_prompt', '')

            if not job_description:
                return jsonify({
                    'success': False,
                    'error': 'Job description is required'
                }), 400

            # Handle file with proper cleanup
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                resume_text = extract_text_from_pdf(filepath)
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)

            # Process with Claude
            try:
                client = get_anthropic_client()
                prompt = f"""
                RESUME:
                {resume_text}

                JOB DESCRIPTION:
                {job_description}

                IMPROVEMENT REQUEST:
                {improvement_prompt}

                Please improve this resume based on the job description and improvement request.
                Focus on matching relevant skills and experience while maintaining accuracy.
                Format the output in a clean, professional way that will work well with ATS systems.
                """

                message = client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=1024,
                    temperature=0.7,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )

                improved_resume = message.content[0].text
                return jsonify({
                    'success': True,
                    'improved_resume': improved_resume
                })

            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Error from Claude API: {str(e)}'
                }), 500

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    return app