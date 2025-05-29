from flask import Flask, request, render_template, jsonify, send_file, Response, session, redirect, url_for
import requests
import time
import io
import tempfile
import os
import atexit
import threading
from pydub import AudioSegment
import logging
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import psycopg2.pool

from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
# app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Global session storage
AUDIO_SESSIONS = {}
SESSION_LOCK = threading.Lock()

# Database connection pool
db_pool = None

# AssemblyAI API Key
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')
if not ASSEMBLYAI_API_KEY:
    logger.error("AssemblyAI API key not found. Please set ASSEMBLYAI_API_KEY environment variable.")
    raise ValueError("AssemblyAI API key is required")

# AssemblyAI headers
headers = {'authorization': ASSEMBLYAI_API_KEY}

# Allowed file extensions
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac', 'ogg'}

def init_database():
    """Initialize database connection pool"""
    global db_pool
    try:
        # Get database URL from environment variable
        database_url = os.getenv('DATABASE_URL')

        # Parse DATABASE_URL (common format for cloud providers)
        # Format: postgresql://user:password@host:port/database
        parsed = urlparse(database_url)
            
        db_pool = psycopg2.pool.ThreadedConnectionPool(
                1, 20,  # min and max connections
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],  # Remove leading '/'
                user=parsed.username,
                password=parsed.password,
                sslmode='require'  # Required for most cloud PostgreSQL services
            )
        
        logger.info("Database connection pool initialized successfully")
        create_tables()
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def get_db_connection():
    """Get a database connection from the pool"""
    global db_pool
    if db_pool:
        return db_pool.getconn()
    else:
        raise Exception("Database pool not initialized")

def return_db_connection(conn):
    """Return a database connection to the pool"""
    global db_pool
    if db_pool and conn:
        db_pool.putconn(conn)

def create_tables():
    """Create necessary database tables"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create transcripts table with audio storage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transcripts (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) UNIQUE NOT NULL,
                transcript_id VARCHAR(255) NOT NULL,
                filename VARCHAR(255) NOT NULL,
                text TEXT,
                confidence FLOAT,
                audio_duration INTEGER,
                speaker_labels BOOLEAN DEFAULT TRUE,
                language_code VARCHAR(10) DEFAULT 'en_us',
                audio_data BYTEA,
                audio_mimetype VARCHAR(100),
                audio_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create utterances table for speaker segments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS utterances (
                id SERIAL PRIMARY KEY,
                transcript_session_id VARCHAR(255) REFERENCES transcripts(session_id) ON DELETE CASCADE,
                speaker VARCHAR(50),
                text TEXT,
                confidence FLOAT,
                start_time INTEGER,
                end_time INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transcripts_session_id ON transcripts(session_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transcripts_created_at ON transcripts(created_at);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_utterances_session_id ON utterances(transcript_session_id);
        """)
        
        conn.commit()
        logger.info("Database tables created successfully")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error creating tables: {e}")
        raise
    finally:
        if conn:
            return_db_connection(conn)

def save_transcript_to_db(session_id, transcript_data, filename, audio_data=None, audio_mimetype=None):
    """Save transcript, utterances, and audio to database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate audio size if data is provided
        audio_size = len(audio_data) if audio_data else None
        
        # Insert transcript with audio data
        cursor.execute("""
            INSERT INTO transcripts (
                session_id, transcript_id, filename, text, confidence, 
                audio_duration, speaker_labels, language_code,
                audio_data, audio_mimetype, audio_size
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id) DO UPDATE SET
                text = EXCLUDED.text,
                confidence = EXCLUDED.confidence,
                audio_duration = EXCLUDED.audio_duration,
                audio_data = EXCLUDED.audio_data,
                audio_mimetype = EXCLUDED.audio_mimetype,
                audio_size = EXCLUDED.audio_size,
                updated_at = CURRENT_TIMESTAMP
        """, (
            session_id,
            transcript_data.get('transcript_id', ''),
            filename,
            transcript_data.get('text', ''),
            transcript_data.get('confidence', 0),
            transcript_data.get('audio_duration', 0),
            True,  # speaker_labels
            'en_us',  # language_code
            audio_data,
            audio_mimetype,
            audio_size
        ))
        
        # Insert utterances
        utterances = transcript_data.get('utterances', [])
        if utterances:
            # Clear existing utterances for this session
            cursor.execute("""
                DELETE FROM utterances WHERE transcript_session_id = %s
            """, (session_id,))
            
            # Insert new utterances
            for utterance in utterances:
                cursor.execute("""
                    INSERT INTO utterances (
                        transcript_session_id, speaker, text, confidence, start_time, end_time
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    session_id,
                    utterance.get('speaker', 'Unknown'),
                    utterance.get('text', ''),
                    utterance.get('confidence', 0),
                    utterance.get('start', 0),
                    utterance.get('end', 0)
                ))
        
        conn.commit()
        logger.info(f"Transcript and audio saved to database: {session_id}")
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error saving transcript to database: {e}")
        return False
    finally:
        if conn:
            return_db_connection(conn)

def get_transcript_from_db(session_id, include_audio=False):
    """Retrieve transcript from database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get transcript (conditionally include audio data)
        if include_audio:
            cursor.execute("""
                SELECT * FROM transcripts WHERE session_id = %s
            """, (session_id,))
        else:
            cursor.execute("""
                SELECT id, session_id, transcript_id, filename, text, confidence, 
                       audio_duration, speaker_labels, language_code, audio_mimetype, 
                       audio_size, created_at, updated_at
                FROM transcripts WHERE session_id = %s
            """, (session_id,))
        
        transcript = cursor.fetchone()
        
        if not transcript:
            return None
            
        # Get utterances
        cursor.execute("""
            SELECT * FROM utterances 
            WHERE transcript_session_id = %s 
            ORDER BY start_time
        """, (session_id,))
        utterances = cursor.fetchall()
        
        return {
            'transcript': dict(transcript),
            'utterances': [dict(u) for u in utterances]
        }
        
    except Exception as e:
        logger.error(f"Error retrieving transcript from database: {e}")
        return None
    finally:
        if conn:
            return_db_connection(conn)

def get_audio_from_db(session_id):
    """Retrieve only audio data from database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT audio_data, audio_mimetype, filename
            FROM transcripts WHERE session_id = %s
        """, (session_id,))
        
        result = cursor.fetchone()
        return dict(result) if result else None
        
    except Exception as e:
        logger.error(f"Error retrieving audio from database: {e}")
        return None
    finally:
        if conn:
            return_db_connection(conn)

def get_all_transcripts():
    """Get all transcripts from database (without audio data)"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT session_id, filename, text, confidence, audio_duration, 
                   audio_size, audio_mimetype, created_at
            FROM transcripts 
            ORDER BY created_at DESC
        """)
        transcripts = cursor.fetchall()
        
        return [dict(t) for t in transcripts]
        
    except Exception as e:
        logger.error(f"Error retrieving all transcripts: {e}")
        return []
    finally:
        if conn:
            return_db_connection(conn)

def delete_transcript_from_db(session_id):
    """Delete transcript and its utterances from database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete transcript (utterances will be deleted due to CASCADE)
        cursor.execute("""
            DELETE FROM transcripts WHERE session_id = %s
        """, (session_id,))
        
        conn.commit()
        logger.info(f"Transcript deleted from database: {session_id}")
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting transcript from database: {e}")
        return False
    finally:
        if conn:
            return_db_connection(conn)

def allowed_file(filename):
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

def cleanup_expired_sessions():
    with SESSION_LOCK:
        current_time = datetime.now()
        expired = [s_id for s_id, data in AUDIO_SESSIONS.items()
                   if current_time - data['created_at'] > timedelta(hours=1)]
        for s_id in expired:
            try:
                AUDIO_SESSIONS[s_id]['processor'].cleanup()
                del AUDIO_SESSIONS[s_id]
                logger.info(f"Cleaned up expired session: {s_id}")
            except Exception as e:
                logger.error(f"Error cleaning up session {s_id}: {e}")

def cleanup_all_sessions():
    with SESSION_LOCK:
        for s_id, data in AUDIO_SESSIONS.items():
            try:
                data['processor'].cleanup()
                logger.info(f"Cleaned up session: {s_id}")
            except Exception as e:
                logger.error(f"Error cleaning up session {s_id}: {e}")
        AUDIO_SESSIONS.clear()
    
    # Close database pool
    global db_pool
    if db_pool:
        db_pool.closeall()

atexit.register(cleanup_all_sessions)

class AudioProcessor:
    def __init__(self):
        self.headers = headers
        self.audio_path = None
        self.audio_segment = None
        self.audio_data = None
        self.audio_mimetype = None
        self.created_at = datetime.now()

    def save_audio_file(self, file):
        try:
            if not allowed_file(file.filename):
                raise ValueError("Invalid file type")
            filename = secure_filename(file.filename)
            if not filename:
                raise ValueError("Invalid filename")
            
            unique_id = str(uuid.uuid4())
            path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_{filename}")
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
        try:
            with open(self.audio_path, 'rb') as f:
                r = requests.post('https://api.assemblyai.com/v2/upload', headers=self.headers, data=f, timeout=300)
                r.raise_for_status()
                return r.json()['upload_url']
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return None

    def request_transcription(self, audio_url):
        try:
            r = requests.post('https://api.assemblyai.com/v2/transcript',
                              headers=self.headers,
                              json={
                                  'audio_url': audio_url,
                                  'speaker_labels': True,
                                  'language_code': 'en_us',
                                  'punctuate': True,
                                  'format_text': True
                              },
                              timeout=30)
            r.raise_for_status()
            return r.json()['id']
        except Exception as e:
            logger.error(f"Transcription request error: {e}")
            return None

    def poll_transcription(self, transcript_id):
        url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        for _ in range(120):
            try:
                r = requests.get(url, headers=self.headers, timeout=30)
                r.raise_for_status()
                result = r.json()
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
        try:
            if not self.audio_segment:
                raise ValueError("Audio not loaded")
            segment = self.audio_segment[start_ms:end_ms]
            buf = io.BytesIO()
            segment.export(buf, format="mp3")
            buf.seek(0)
            return buf
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return None

    def get_audio_data(self):
        """Return the stored audio data and mimetype"""
        return self.audio_data, self.audio_mimetype

    def cleanup(self):
        if self.audio_path and os.path.exists(self.audio_path):
            try:
                os.remove(self.audio_path)
            except Exception as e:
                logger.warning(f"Cleanup failed: {e}")



# Initialize database on startup
init_database()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcripts')
def past_transcripts():
    """Display all past transcripts"""
    try:
        transcripts = get_all_transcripts()
        return render_template('transcripts.html', transcripts=transcripts)
    except Exception as e:
        logger.error(f"Error loading transcripts page: {e}")
        return render_template('transcripts.html', transcripts=[], error="Failed to load transcripts")

@app.route('/api/transcript/<session_id>', methods=['DELETE'])
def delete_transcript(session_id):
    """API endpoint to delete a specific transcript"""
    try:
        success = delete_transcript_from_db(session_id)
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Failed to delete transcript'}), 500
    except Exception as e:
        logger.error(f"Error deleting transcript: {e}")
        return jsonify({'error': 'Failed to delete transcript'}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files or request.files['file'].filename == '':
            return jsonify({'error': 'No file selected'}), 400

        file = request.files['file']
        if not allowed_file(file.filename):
            return jsonify({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

        cleanup_expired_sessions()

        processor = AudioProcessor()
        if not processor.save_audio_file(file):
            return jsonify({'error': 'File save failed'}), 500

        audio_url = processor.upload_to_assemblyai()
        if not audio_url:
            processor.cleanup()
            return jsonify({'error': 'Upload failed'}), 500

        transcript_id = processor.request_transcription(audio_url)
        if not transcript_id:
            processor.cleanup()
            return jsonify({'error': 'Transcription request failed'}), 500

        result = processor.poll_transcription(transcript_id)
        if not result:
            processor.cleanup()
            return jsonify({'error': 'Transcription timed out or failed'}), 500

        session_id = str(uuid.uuid4())
        
        # Save to database with audio data
        transcript_data = {
            'transcript_id': transcript_id,
            'text': result.get('text', ''),
            'utterances': result.get('utterances', []),
            'confidence': result.get('confidence', 0),
            'audio_duration': result.get('audio_duration', 0)
        }
        
        audio_data, audio_mimetype = processor.get_audio_data()
        save_success = save_transcript_to_db(
            session_id, 
            transcript_data, 
            file.filename,
            audio_data=audio_data,
            audio_mimetype=audio_mimetype
        )
        
        if not save_success:
            logger.warning(f"Failed to save transcript to database for session: {session_id}")

        with SESSION_LOCK:
            AUDIO_SESSIONS[session_id] = {
                'processor': processor,
                'created_at': datetime.now()
            }

        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'result': transcript_data,
            'saved_to_db': save_success,
            'audio_stored': save_success and audio_data is not None
        })

    except Exception as e:
        logger.error(f"Upload route error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/audio_segment/<session_id>/<int:start_ms>/<int:end_ms>')
def get_audio_segment(session_id, start_ms, end_ms):
    try:
        # First try to get from active session
        with SESSION_LOCK:
            processor = AUDIO_SESSIONS.get(session_id, {}).get('processor')

        if processor:
            # Use active session
            if start_ms >= end_ms:
                return jsonify({'error': 'Invalid timestamp range'}), 400

            buffer = processor.extract_audio_segment(start_ms, end_ms)
            if not buffer:
                return jsonify({'error': 'Segment extraction failed'}), 500

            return send_file(
                buffer,
                mimetype='audio/mp3',
                as_attachment=True,
                download_name=f'segment_{start_ms}_{end_ms}.mp3'
            )
        else:
            # Try to reconstruct from database
            audio_data = get_audio_from_db(session_id)
            if not audio_data or not audio_data['audio_data']:
                return jsonify({'error': 'Session not found and no stored audio'}), 404

            # Create AudioSegment from stored data
            audio_buffer = io.BytesIO(audio_data['audio_data'])
            audio_segment = AudioSegment.from_file(audio_buffer)
            
            if start_ms >= end_ms:
                return jsonify({'error': 'Invalid timestamp range'}), 400

            segment = audio_segment[start_ms:end_ms]
            buffer = io.BytesIO()
            segment.export(buffer, format="mp3")
            buffer.seek(0)

            return send_file(
                buffer,
                mimetype='audio/mp3',
                as_attachment=True,
                download_name=f'segment_{start_ms}_{end_ms}.mp3'
            )

    except Exception as e:
        logger.error(f"Audio segment error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/cleanup/<session_id>', methods=['POST'])
def cleanup_session(session_id):
    try:
        with SESSION_LOCK:
            if session_id in AUDIO_SESSIONS:
                AUDIO_SESSIONS[session_id]['processor'].cleanup()
                del AUDIO_SESSIONS[session_id]
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Session cleanup error: {e}")
        return jsonify({'error': 'Cleanup failed'}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Max is 16MB'}), 413

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)