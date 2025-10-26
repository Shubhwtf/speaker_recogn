"""
Audio processing and AssemblyAI integration
"""
import os
import io
import uuid
import time
import requests
from datetime import datetime
from pydub import AudioSegment
from werkzeug.utils import secure_filename
from config import ASSEMBLYAI_HEADERS, ALLOWED_EXTENSIONS, UPLOAD_FOLDER, logger


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_mimetype_from_extension(filename):
    """Get MIME type based on file extension"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    mimetype_map = {
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'm4a': 'audio/mp4',
        'flac': 'audio/flac',
        'ogg': 'audio/ogg'
    }
    return mimetype_map.get(ext, 'audio/mpeg')


class AudioProcessor:
    """Handles audio file processing and transcription"""
    
    def __init__(self):
        self.headers = ASSEMBLYAI_HEADERS
        self.audio_path = None
        self.audio_segment = None
        self.audio_data = None
        self.audio_mimetype = None
        self.created_at = datetime.now()

    def save_audio_file(self, file):
        """Save uploaded audio file to temporary location"""
        try:
            if not allowed_file(file.filename):
                raise ValueError("Invalid file type")
            
            filename = secure_filename(file.filename)
            if not filename:
                raise ValueError("Invalid filename")
            
            unique_id = str(uuid.uuid4())
            path = os.path.join(UPLOAD_FOLDER, f"{unique_id}_{filename}")
            file.save(path)
            
            self.audio_path = path
            self.audio_segment = AudioSegment.from_file(path)
            self.audio_mimetype = get_mimetype_from_extension(file.filename)
            
            # Read audio data into memory for database storage
            with open(path, 'rb') as audio_file:
                self.audio_data = audio_file.read()
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving audio: {e}")
            if self.audio_path and os.path.exists(self.audio_path):
                os.remove(self.audio_path)
            return False

    def upload_to_assemblyai(self):
        """Upload audio file to AssemblyAI"""
        try:
            with open(self.audio_path, 'rb') as f:
                response = requests.post(
                    'https://api.assemblyai.com/v2/upload',
                    headers=self.headers,
                    data=f,
                    timeout=300
                )
                response.raise_for_status()
                return response.json()['upload_url']
                
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return None

    def request_transcription(self, audio_url):
        """Request transcription from AssemblyAI"""
        try:
            response = requests.post(
                'https://api.assemblyai.com/v2/transcript',
                headers=self.headers,
                json={
                    'audio_url': audio_url,
                    'speaker_labels': True,
                    'language_code': 'en_us',
                    'punctuate': True,
                    'format_text': True
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()['id']
            
        except Exception as e:
            logger.error(f"Transcription request error: {e}")
            return None

    def poll_transcription(self, transcript_id):
        """Poll AssemblyAI for transcription completion"""
        url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        
        for _ in range(120): 
            try:
                response = requests.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                result = response.json()
                
                if result['status'] == 'completed':
                    return result
                elif result['status'] == 'error':
                    logger.error(f"Transcription error: {result.get('error', 'Unknown')}")
                    return None
                    
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(5)
                
        logger.error("Polling timeout")
        return None

    def extract_audio_segment(self, start_ms, end_ms):
        """Extract a segment of audio between start and end times"""
        try:
            if not self.audio_segment:
                raise ValueError("Audio not loaded")
                
            segment = self.audio_segment[start_ms:end_ms]
            buffer = io.BytesIO()
            segment.export(buffer, format="mp3")
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return None

    def get_audio_data(self):
        """Return the stored audio data and mimetype"""
        return self.audio_data, self.audio_mimetype

    def cleanup(self):
        """Clean up temporary audio file"""
        if self.audio_path and os.path.exists(self.audio_path):
            try:
                os.remove(self.audio_path)
                logger.info(f"Cleaned up audio file: {self.audio_path}")
            except Exception as e:
                logger.error(f"Error cleaning up {self.audio_path}: {e}")

