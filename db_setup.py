#!/usr/bin/env python3
"""
Database setup script for the transcription app with audio storage
Run this script to create the database and tables
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from urllib.parse import urlparse
from dotenv import load_dotenv

def create_database_if_not_exists():
    """Create database if it doesn't exist (for local development)"""
    load_dotenv()
    
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # For cloud databases, the database usually already exists
        print("Using cloud database URL - skipping database creation")
        return
    
    # For local development
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'password')
    }
    
    db_name = os.getenv('DB_NAME', 'transcripts_db')
    
    try:
        # Connect to PostgreSQL server (not specific database)
        conn = psycopg2.connect(**db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Database '{db_name}' created successfully")
        else:
            print(f"Database '{db_name}' already exists")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error creating database: {e}")
        sys.exit(1)

def create_tables():
    """Create application tables"""
    load_dotenv()
    
    try:
        # Get database connection
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            parsed = urlparse(database_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password,
                sslmode='require'
            )
        else:
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME', 'transcripts_db'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', 'password')
            }
            conn = psycopg2.connect(**db_config)
        
        cursor = conn.cursor()
        
        # Create transcripts table with audio storage columns
        print("Creating transcripts table with audio storage...")
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
        
        # Create utterances table
        print("Creating utterances table...")
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
        
        # Create indexes
        print("Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transcripts_session_id ON transcripts(session_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transcripts_created_at ON transcripts(created_at);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_utterances_session_id ON utterances(transcript_session_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transcripts_filename ON transcripts(filename);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transcripts_audio_size ON transcripts(audio_size);
        """)
        
        # Create updated_at trigger function
        print("Creating trigger for updated_at...")
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        
        # Create trigger
        cursor.execute("""
            DROP TRIGGER IF EXISTS update_transcripts_updated_at ON transcripts;
            CREATE TRIGGER update_transcripts_updated_at
                BEFORE UPDATE ON transcripts
                FOR EACH ROW
                EXECUTE PROCEDURE update_updated_at_column();
        """)
        
        conn.commit()
        print("Tables and indexes created successfully!")
        
        # Show table info
        cursor.execute("""
            SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name IN ('transcripts', 'utterances')
            ORDER BY table_name, ordinal_position;
        """)
        
        results = cursor.fetchall()
        print("\nDatabase schema:")
        current_table = None
        for row in results:
            table_name, column_name, data_type, is_nullable = row
            if table_name != current_table:
                print(f"\n{table_name.upper()} table:")
                current_table = table_name
            nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
            print(f"  - {column_name}: {data_type} ({nullable})")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error creating tables: {e}")
        sys.exit(1)

def migrate_existing_tables():
    """Add audio columns to existing transcripts table"""
    load_dotenv()
    
    try:
        # Get database connection
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            parsed = urlparse(database_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password,
                sslmode='require'
            )
        else:
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME', 'transcripts_db'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', 'password')
            }
            conn = psycopg2.connect(**db_config)
        
        cursor = conn.cursor()
        
        print("Checking if migration is needed...")
        
        # Check if audio columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'transcripts' AND column_name IN ('audio_data', 'audio_mimetype', 'audio_size')
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        if len(existing_columns) == 3:
            print("Audio columns already exist - no migration needed")
            cursor.close()
            conn.close()
            return
        
        print("Adding audio storage columns to existing transcripts table...")
        
        # Add audio columns if they don't exist
        if 'audio_data' not in existing_columns:
            cursor.execute("ALTER TABLE transcripts ADD COLUMN audio_data BYTEA")
            print("  - Added audio_data column")
        
        if 'audio_mimetype' not in existing_columns:
            cursor.execute("ALTER TABLE transcripts ADD COLUMN audio_mimetype VARCHAR(100)")
            print("  - Added audio_mimetype column")
        
        if 'audio_size' not in existing_columns:
            cursor.execute("ALTER TABLE transcripts ADD COLUMN audio_size INTEGER")
            print("  - Added audio_size column")
        
        # Add new indexes
        print("Adding new indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transcripts_filename ON transcripts(filename);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transcripts_audio_size ON transcripts(audio_size);
        """)
        
        conn.commit()
        print("Migration completed successfully!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)

def test_connection():
    """Test database connection"""
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
                sslmode='require'
            )
        else:
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME', 'transcripts_db'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', 'password')
            }
            conn = psycopg2.connect(**db_config)
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Database connection successful!")
        print(f"PostgreSQL version: {version[0]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

def show_storage_stats():
    """Show database storage statistics"""
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
                sslmode='require'
            )
        else:
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME', 'transcripts_db'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', 'password')
            }
            conn = psycopg2.connect(**db_config)
        
        cursor = conn.cursor()
        
        # Get table sizes
        cursor.execute("""
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
            FROM pg_tables 
            WHERE tablename IN ('transcripts', 'utterances')
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        """)
        
        print("\n📊 Database storage statistics:")
        for row in cursor.fetchall():
            schema, table, size = row
            print(f"  {table}: {size}")
        
        # Get transcript count and audio storage info
        cursor.execute("""
            SELECT 
                COUNT(*) as total_transcripts,
                COUNT(audio_data) as with_audio,
                pg_size_pretty(SUM(audio_size)) as total_audio_size,
                pg_size_pretty(AVG(audio_size)) as avg_audio_size
            FROM transcripts;
        """)
        
        stats = cursor.fetchone()
        if stats:
            total, with_audio, total_size, avg_size = stats
            print(f"\n📈 Transcript statistics:")
            print(f"  Total transcripts: {total}")
            print(f"  With audio: {with_audio}")
            print(f"  Total audio storage: {total_size or '0 bytes'}")
            print(f"  Average audio size: {avg_size or '0 bytes'}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error getting storage stats: {e}")

def main():
    """Main setup function"""
    print("🚀 Setting up transcription database with audio storage...")
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--migrate":
            print("\n🔄 Running migration mode...")
            test_connection()
            migrate_existing_tables()
            show_storage_stats()
            print("\n✅ Migration completed successfully!")
            return
        elif sys.argv[1] == "--stats":
            print("\n📊 Showing storage statistics...")
            test_connection()
            show_storage_stats()
            return
        elif sys.argv[1] == "--help":
            print("\nUsage:")
            print("  python setup_db.py           # Full setup (default)")
            print("  python setup_db.py --migrate # Migrate existing database")
            print("  python setup_db.py --stats   # Show storage statistics")
            print("  python setup_db.py --help    # Show this help")
            return
    
    # Full setup
    # Test connection first
    print("\n1. Testing database connection...")
    test_connection()
    
    # Create database (for local development)
    print("\n2. Creating database if needed...")
    create_database_if_not_exists()
    
    # Create tables
    print("\n3. Creating tables and indexes...")
    create_tables()
    
    # Show storage stats
    print("\n4. Database statistics...")
    show_storage_stats()
    
    print("\n✅ Database setup completed successfully!")
    print("\nYou can now run your Flask application.")
    print("\nUseful commands:")
    print("  python setup_db.py --migrate  # Migrate existing database")
    print("  python setup_db.py --stats    # Show storage statistics")

if __name__ == "__main__":
    main()