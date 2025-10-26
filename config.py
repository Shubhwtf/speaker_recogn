"""
Configuration and constants for the application
"""
import os
import tempfile
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = tempfile.mkdtemp()
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')
if not ASSEMBLYAI_API_KEY:
    logger.error("AssemblyAI API key not found. Please set ASSEMBLYAI_API_KEY environment variable.")
    raise ValueError("AssemblyAI API key is required")
ASSEMBLYAI_HEADERS = {'authorization': ASSEMBLYAI_API_KEY}

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL not found. Please set DATABASE_URL environment variable.")
    raise ValueError("DATABASE_URL is required")

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac', 'ogg'}

PORT = int(os.getenv('PORT', 8000))
DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

SESSION_EXPIRY_HOURS = 24

logger.info("Configuration loaded successfully")

