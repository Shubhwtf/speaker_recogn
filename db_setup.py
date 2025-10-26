import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from urllib.parse import urlparse
from dotenv import load_dotenv

def create_database_if_not_exists():
    load_dotenv()
    
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        print("Using cloud database - skipping creation")
        return
    
    db_config = {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    }
    
    db_name = os.getenv('DB_NAME')
    
    try:
        conn = psycopg2.connect(**db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Created database '{db_name}'")
        else:
            print(f"Database '{db_name}' exists")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def create_tables():
    load_dotenv()
    
    try:
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            parsed = urlparse(database_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password,
                sslmode='prefer'
            )
        else:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'transcripts_db'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'password')
            )
        
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
        
        # Migrate user_id if needed
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='transcripts' AND column_name='user_id'
                ) THEN
                    ALTER TABLE transcripts ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;
                END IF;
            END $$;
        """)
        
        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_session_id ON transcripts(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_user_id ON transcripts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_created_at ON transcripts(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_utterances_session_id ON utterances(transcript_session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_filename ON transcripts(filename)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_audio_size ON transcripts(audio_size)")
        
        # Updated timestamp trigger
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        
        cursor.execute("""
            DROP TRIGGER IF EXISTS update_transcripts_updated_at ON transcripts;
            CREATE TRIGGER update_transcripts_updated_at
                BEFORE UPDATE ON transcripts
                FOR EACH ROW
                EXECUTE PROCEDURE update_updated_at_column();
        """)
        
        conn.commit()
        print("Tables created")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def migrate_existing_tables():
    load_dotenv()
    
    try:
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            parsed = urlparse(database_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password,
                sslmode='prefer'
            )
        else:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'transcripts_db'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'password')
            )
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'transcripts' AND column_name IN ('audio_data', 'audio_mimetype', 'audio_size')
        """)
        existing = [row[0] for row in cursor.fetchall()]
        
        if len(existing) == 3:
            print("Already migrated")
            cursor.close()
            conn.close()
            return
        
        if 'audio_data' not in existing:
            cursor.execute("ALTER TABLE transcripts ADD COLUMN audio_data BYTEA")
        
        if 'audio_mimetype' not in existing:
            cursor.execute("ALTER TABLE transcripts ADD COLUMN audio_mimetype VARCHAR(100)")
        
        if 'audio_size' not in existing:
            cursor.execute("ALTER TABLE transcripts ADD COLUMN audio_size INTEGER")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_filename ON transcripts(filename)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_audio_size ON transcripts(audio_size)")
        
        conn.commit()
        print("Migration done")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def show_stats():
    load_dotenv()
    
    try:
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            parsed = urlparse(database_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password,
                sslmode='prefer'
            )
        else:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'transcripts_db'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'password')
            )
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(audio_data) as with_audio,
                pg_size_pretty(SUM(audio_size)) as total_size
            FROM transcripts;
        """)
        
        stats = cursor.fetchone()
        if stats:
            total, with_audio, size = stats
            print(f"\nTranscripts: {total}")
            print(f"With audio: {with_audio}")
            print(f"Total size: {size or '0 bytes'}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    load_dotenv()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--migrate":
            migrate_existing_tables()
        elif sys.argv[1] == "--stats":
            show_stats()
        else:
            print("Usage: python setup_db.py [--migrate|--stats]")
    else:
        create_database_if_not_exists()
        create_tables()
        print("Done")