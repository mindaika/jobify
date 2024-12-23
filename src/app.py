import os
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader 

# Initialize Flask app with static folder configuration
app = Flask(__name__, 
           static_folder='static',  # Directory for built frontend files
           static_url_path='')      # Serve static files from root URL

app.config.update(
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    UPLOAD_FOLDER='/tmp',                 # Temporary storage for uploads
)

ALLOWED_EXTENSIONS = {'pdf'}

def get_anthropic_client():
    """Get a new Anthropic client instance"""
    import anthropic
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    return anthropic.Anthropic(api_key=api_key)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    """Extract text from a PDF file"""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")

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
    return jsonify({"status": "ok"})

@app.route('/api/process_resume', methods=['POST'])
def process_resume():
    """Process uploaded resume and job description using Claude"""
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
                model="claude-3-opus-20240229",
                max_tokens=4000,
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004)