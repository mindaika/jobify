import os
from typing import Union
from pathlib import Path
import httpx
from PyPDF2 import PdfReader
import markdown
import anthropic

ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt'}

class DocumentProcessor:
    def __init__(self, api_key: str):
        """Initialize the document processor with Claude API key."""
        http_client = httpx.Client()
        self.client = anthropic.Anthropic(
            api_key=api_key, 
            http_client=http_client
        )
        
    def process_document(self, document_text: str, job_description: str,
                        improvement_prompt: str) -> str:
        """
        Process document with Claude and return improved text.
        """
        full_prompt = f"""
        RESUME:
        {document_text}

        JOB DESCRIPTION:
        {job_description}

        IMPROVEMENT REQUEST:
        {improvement_prompt}

        Please improve this resume based on the job description and improvement request.
        Focus on matching relevant skills and experience while maintaining accuracy.
        Format the output in a clean, professional way that will work well with ATS systems.
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=4096,  # Increased token limit
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": full_prompt
                }]
            )
            return response.content[0].text
                
        except Exception as e:
            raise Exception(f"Error calling Claude API: {str(e)}")

def get_anthropic_client():
    """Get a new Anthropic client instance"""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    return DocumentProcessor(api_key)

def allowed_file(filename):
    """Check if a filename has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")

def extract_text_from_file(file_path: Union[str, Path], file_type: str = None) -> str:
    """Extract text from various file types."""
    file_path = Path(file_path)
    
    if file_type is None:
        file_type = file_path.suffix.lower()[1:]
    
    if file_type == 'pdf':
        return extract_text_from_pdf(file_path)
    elif file_type == 'md':
        with open(file_path, 'r', encoding='utf-8') as f:
            return markdown.markdown(f.read())
    elif file_type == 'txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        raise ValueError(f"Unsupported file type: {file_type}")