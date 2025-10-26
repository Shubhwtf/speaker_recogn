"""
Main Flask application entry point
"""
import atexit
from flask import Flask
from flask_cors import CORS

from config import UPLOAD_FOLDER, MAX_CONTENT_LENGTH, PORT, DEBUG, logger
from database import init_database, close_database
from api_routes import register_routes, AUDIO_SESSIONS, SESSION_LOCK


def create_app():
    """Create and configure the Flask application"""
    
    # Initialize Flask app
    app = Flask(__name__)
    CORS(app)
    
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    
    # Initializing database
    init_database()
    register_routes(app)
    
    logger.info("Flask application created successfully")
    return app


def cleanup_all_sessions():
    """Clean up all sessions and close database on shutdown"""
    with SESSION_LOCK:
        for s_id, data in AUDIO_SESSIONS.items():
            try:
                data['processor'].cleanup()
                logger.info(f"Cleaned up session: {s_id}")
            except Exception as e:
                logger.error(f"Error cleaning up session {s_id}: {e}")
        AUDIO_SESSIONS.clear()
    
    close_database()
    logger.info("Application shutdown complete")

atexit.register(cleanup_all_sessions)

app = create_app()


if __name__ == '__main__':
    logger.info(f"Starting server on port {PORT} (debug={DEBUG})")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)

