"""
Database operations and connection management
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import psycopg2.pool
from urllib.parse import urlparse
from config import DATABASE_URL, logger

db_pool = None

def init_database():
    """Initialize database connection pool"""
    global db_pool
    try:
        parsed = urlparse(DATABASE_URL)
        
        sslmode = 'require'
            
        db_pool = psycopg2.pool.ThreadedConnectionPool(
            1, 20,
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            sslmode=sslmode,
            connect_timeout=10,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5
        )
        
        logger.info("Database connection pool initialized successfully")
        create_tables()
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def get_db_connection():
    """Get a database connection from the pool with retry logic for NeonDB"""
    global db_pool
    if not db_pool:
        raise Exception("Database pool not initialized")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            conn.commit()
            return conn
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            if conn:
                try:
                    db_pool.putconn(conn, close=True)
                except:
                    pass
            if attempt == max_retries - 1:
                raise
    return db_pool.getconn()

def return_db_connection(conn):
    """Return a database connection to the pool"""
    global db_pool
    if db_pool and conn:
        try:
            if not conn.closed:
                conn.rollback()
            db_pool.putconn(conn)
        except Exception as e:
            logger.warning(f"Error returning connection to pool: {e}")
            try:
                conn.close()
            except:
                pass

def create_tables():
    """Create necessary database tables"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                is_premium BOOLEAN DEFAULT FALSE,
                premium_expiry TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
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
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
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
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_session_id ON transcripts(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_user_id ON transcripts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_created_at ON transcripts(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_utterances_session_id ON utterances(transcript_session_id)")
        
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

def save_transcript_to_db(session_id, transcript_data, filename, audio_data=None, audio_mimetype=None, user_id=None):
    """Save transcript, utterances, and audio to database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        audio_size = len(audio_data) if audio_data else None
        
        cursor.execute("""
            INSERT INTO transcripts (
                session_id, transcript_id, filename, text, confidence, 
                audio_duration, speaker_labels, language_code,
                audio_data, audio_mimetype, audio_size, user_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id) DO UPDATE SET
                text = EXCLUDED.text,
                confidence = EXCLUDED.confidence,
                audio_duration = EXCLUDED.audio_duration,
                audio_data = EXCLUDED.audio_data,
                audio_mimetype = EXCLUDED.audio_mimetype,
                audio_size = EXCLUDED.audio_size,
                user_id = EXCLUDED.user_id,
                updated_at = CURRENT_TIMESTAMP
        """, (
            session_id,
            transcript_data.get('transcript_id', ''),
            filename,
            transcript_data.get('text', ''),
            transcript_data.get('confidence', 0),
            transcript_data.get('audio_duration', 0),
            True,
            'en_us',
            audio_data,
            audio_mimetype,
            audio_size,
            user_id
        ))
        
        # Insert utterances
        utterances = transcript_data.get('utterances', [])
        if utterances:
            cursor.execute("DELETE FROM utterances WHERE transcript_session_id = %s", (session_id,))
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
        logger.info(f"Transcript saved successfully: {session_id}")
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error saving transcript: {e}")
        return False
    finally:
        if conn:
            return_db_connection(conn)

def get_transcript_from_db(session_id, include_audio=False, user_id=None):
    """Retrieve transcript from database, optionally filtering by user_id"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if user_id is not None:
            where_clause = "WHERE session_id = %s AND user_id = %s"
            params = (session_id, user_id)
        else:
            where_clause = "WHERE session_id = %s"
            params = (session_id,)
        
        if include_audio:
            cursor.execute(f"SELECT * FROM transcripts {where_clause}", params)
        else:
            cursor.execute(f"""
                SELECT id, session_id, transcript_id, filename, text, confidence, 
                       audio_duration, speaker_labels, language_code, audio_mimetype, 
                       audio_size, created_at, updated_at
                FROM transcripts {where_clause}
            """, params)
        
        transcript = cursor.fetchone()
        if not transcript:
            return None
            
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
        logger.error(f"Error retrieving transcript: {e}")
        return None
    finally:
        if conn:
            return_db_connection(conn)

def get_all_transcripts(user_id=None):
    """Get all transcripts, optionally filtered by user_id"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if user_id is not None:
            cursor.execute("""
                SELECT session_id, filename, text, confidence, audio_duration, 
                       audio_size, audio_mimetype, created_at
                FROM transcripts 
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT session_id, filename, text, confidence, audio_duration, 
                       audio_size, audio_mimetype, created_at
                FROM transcripts 
                ORDER BY created_at DESC
            """)
        
        transcripts = cursor.fetchall()
        return [dict(t) for t in transcripts]
        
    except Exception as e:
        logger.error(f"Error retrieving transcripts: {e}")
        return []
    finally:
        if conn:
            return_db_connection(conn)

def delete_transcript_from_db(session_id, user_id=None):
    """Delete transcript and its utterances from database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user_id is not None:
            cursor.execute("DELETE FROM transcripts WHERE session_id = %s AND user_id = %s", 
                          (session_id, user_id))
        else:
            cursor.execute("DELETE FROM transcripts WHERE session_id = %s", (session_id,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        if deleted_count > 0:
            logger.info(f"Transcript deleted: {session_id}")
            return True
        else:
            logger.warning(f"Transcript not found or unauthorized: {session_id}")
            return False
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting transcript: {e}")
        return False
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
            FROM transcripts 
            WHERE session_id = %s
        """, (session_id,))
        
        result = cursor.fetchone()
        return dict(result) if result else None
        
    except Exception as e:
        logger.error(f"Error retrieving audio: {e}")
        return None
    finally:
        if conn:
            return_db_connection(conn)

def close_database():
    """Close all database connections"""
    global db_pool
    if db_pool:
        db_pool.closeall()
        logger.info("Database connection pool closed")

