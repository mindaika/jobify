import os
from typing import Union, Optional
from pathlib import Path
import httpx
from PyPDF2 import PdfReader
import markdown
import anthropic
from .auth import AuthError

ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt'}

class DocumentProcessor:
    """Handles document processing with Claude API."""
    
    def __init__(self, api_key: str):
        """
        Initialize the document processor.
        
        Args:
            api_key: Anthropic API key
        """
        try:
            self.client = anthropic.Anthropic(api_key=api_key)
        except Exception as e:
            raise AuthError(f"Failed to initialize Anthropic client: {str(e)}", 500)
        
    def process_document(self, 
                        document_text: str, 
                        job_description: str,
                        improvement_prompt: str) -> str:
        """
        Process document with Claude and return improved text.
        
        Args:
            document_text: Original resume text
            job_description: Job description text
            improvement_prompt: Instructions for improvement
            
        Returns:
            str: Improved resume text
            
        Raises:
            AuthError: If API call fails
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
        Ensure the information in the updated resume is accurate and relevant. Focus on quality over quantity.
        Try to match keywords of technologies listed. Return only the resume text, formatted in markdown, 
        without any additional comments.
        """
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-0",
                max_tokens=4096,
                temperature=0.9,
                messages=[{
                    "role": "user",
                    "content": full_prompt
                }]
            )
            return response.content[0].text
                
        except Exception as e:
            raise AuthError(f"Error calling Claude API: {str(e)}", 500)

def get_anthropic_client() -> DocumentProcessor:
    """
    Get a new Anthropic client instance.
    
    Returns:
        DocumentProcessor: Initialized document processor
        
    Raises:
        AuthError: If API key is missing or invalid
    """
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise AuthError("ANTHROPIC_API_KEY environment variable is not set", 500)
    return DocumentProcessor(api_key)

def extract_text_from_pdf(file_path: Union[str, Path]) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        str: Extracted text
        
    Raises:
        ValueError: If file reading fails
    """
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise ValueError(f"Error extracting text from PDF: {str(e)}")

def extract_text_from_file(file_path: Union[str, Path], 
                          file_type: Optional[str] = None) -> str:
    """
    Extract text from various file types.
    
    Args:
        file_path: Path to file
        file_type: Optional file type override
        
    Returns:
        str: Extracted text
        
    Raises:
        ValueError: If file type is unsupported or reading fails
    """
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