"""
User database operations
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def create_user_tables(conn):
    """Create user-related tables"""
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
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    """)
    
    cursor.execute("""
        ALTER TABLE transcripts 
        ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_transcripts_user_id ON transcripts(user_id);
    """)
    
    conn.commit()
    logger.info("User tables created successfully")

def create_user(conn, email, password_hash, full_name=None):
    """Create a new user"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            INSERT INTO users (email, password_hash, full_name)
            VALUES (%s, %s, %s)
            RETURNING id, email, full_name, is_premium, created_at
        """, (email, password_hash, full_name))
        
        user = cursor.fetchone()
        conn.commit()
        
        return dict(user) if user else None
    except psycopg2.IntegrityError:
        conn.rollback()
        return None
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating user: {e}")
        return None

def get_user_by_email(conn, email):
    """Get user by email"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, email, password_hash, full_name, is_premium, premium_expiry, created_at
            FROM users
            WHERE email = %s
        """, (email,))
        
        user = cursor.fetchone()
        return dict(user) if user else None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

def get_user_by_id(conn, user_id):
    """Get user by ID"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, email, full_name, is_premium, premium_expiry, created_at
            FROM users
            WHERE id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        return dict(user) if user else None
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}")
        return None

def upgrade_to_premium(conn, user_id):
    """Upgrade user to premium"""
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users
            SET is_premium = TRUE,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (user_id,))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error upgrading user to premium: {e}")
        return False

def get_user_transcript_count(conn, user_id):
    """Get the number of transcripts for a user"""
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM transcripts
            WHERE user_id = %s
        """, (user_id,))
        
        count = cursor.fetchone()[0]
        return count
    except Exception as e:
        logger.error(f"Error getting transcript count: {e}")
        return 0

def can_create_transcript(conn, user_id):
    """Check if user can create a new transcript (based on limits)"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT is_premium FROM users WHERE id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        if not user:
            return False
        if user['is_premium']:
            return True
        
        count = get_user_transcript_count(conn, user_id)
        return count < 3
        
    except Exception as e:
        logger.error(f"Error checking transcript limit: {e}")
        return False

