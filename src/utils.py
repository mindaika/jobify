import os
from typing import Union
from pathlib import Path
import httpx
from PyPDF2 import PdfReader
import markdown
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.units import inch
import anthropic

ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt'}

class DocumentProcessor:
    def __init__(self, api_key: str):
        """Initialize the document processor with Claude API key."""
        # Create httpx client with explicit proxy settings
        http_client = httpx.Client()
        self.client = anthropic.Anthropic(
            api_key=api_key, 
            http_client=http_client
        )
        
    def process_document(self, document_text: str, job_description: str, 
                        improvement_prompt: str, output_format: str = 'text') -> Union[str, bytes]:
        """
        Process document with Claude and return either text or PDF.
        """
        # Prepare the complete prompt for Claude
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
        
        # Call Claude API with appropriate version handling
        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": full_prompt
                }]
            )
            improved_text = response.content[0].text
            
            # Return based on requested format
            if output_format == 'pdf':
                return self._generate_pdf(improved_text)
            else:
                return improved_text
                
        except Exception as e:
            raise Exception(f"Error calling Claude API: {str(e)}")
    
    def _generate_pdf(self, text: str) -> bytes:
        """Generate a PDF document from text and return as bytes."""
        from io import BytesIO
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            spaceAfter=12
        )
        
        story = []
        paragraphs = text.split('\n\n')
        for para in paragraphs:
            if para.strip():
                story.append(Paragraph(para.replace('\n', '<br/>'), normal_style))
        
        doc.build(story)
        return buffer.getvalue()

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