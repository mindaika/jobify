import os
from PyPDF2 import PdfReader

ALLOWED_EXTENSIONS = {'pdf'}

def get_anthropic_client():
    """Get a new Anthropic client instance"""
    from anthropic import Anthropic
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    try:
        return Anthropic(api_key=api_key)
    except TypeError as e:
        raise Exception(f"Error initializing Anthropic client: {str(e)}")


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