"""
API route handlers for the app
"""
import io
import os
import uuid
import threading
import razorpay
from datetime import datetime, timedelta
from flask import request, jsonify, send_file
from pydub import AudioSegment

from config import ALLOWED_EXTENSIONS, logger
from database import (
    get_db_connection, return_db_connection, save_transcript_to_db,
    get_transcript_from_db, get_all_transcripts, delete_transcript_from_db,
    get_audio_from_db
)
from audio_processor import AudioProcessor, allowed_file
from gemini_service import analyze_transcript
from auth_service import hash_password, verify_password, generate_token, token_required
from user_db import (
    create_user, get_user_by_email, get_user_by_id,
    upgrade_to_premium, get_user_transcript_count, can_create_transcript
)

AUDIO_SESSIONS = {}
SESSION_LOCK = threading.Lock()
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def cleanup_expired_sessions():
    """Clean up sessions older than 1 hour"""
    with SESSION_LOCK:
        current_time = datetime.now()
        expired = [
            s_id for s_id, data in AUDIO_SESSIONS.items()
            if current_time - data['created_at'] > timedelta(hours=1)
        ]
        for s_id in expired:
            try:
                AUDIO_SESSIONS[s_id]['processor'].cleanup()
                del AUDIO_SESSIONS[s_id]
                logger.info(f"Cleaned up expired session: {s_id}")
            except Exception as e:
                logger.error(f"Error cleaning up session {s_id}: {e}")


def register_routes(app):
    """Register all API routes with the Flask app"""
    @app.route('/')
    def index():
        """API information endpoint"""
        return jsonify({
            'message': 'AI Speaker Recognition API',
            'version': '2.0',
            'endpoints': {
                'auth': {
                    'signup': 'POST /api/auth/signup',
                    'login': 'POST /api/auth/login',
                    'me': 'GET /api/auth/me',
                    'upgrade': 'POST /api/auth/upgrade'
                },
                'transcripts': {
                    'upload': 'POST /upload',
                    'list': 'GET /api/transcripts',
                    'get': 'GET /api/transcript/<id>',
                    'delete': 'DELETE /api/transcript/<id>',
                    'analyze': 'POST /api/analyze/<id>'
                }
            }
        })

    @app.route('/api/auth/signup', methods=['POST'])
    def signup():
        """Register a new user"""
        try:
            data = request.get_json()
            
            if not data or not data.get('email') or not data.get('password'):
                return jsonify({'error': 'Email and password are required'}), 400
            
            email = data['email'].lower().strip()
            password = data['password']
            full_name = data.get('full_name', '').strip()
            
            if '@' not in email:
                return jsonify({'error': 'Invalid email format'}), 400
            
            if len(password) < 6:
                return jsonify({'error': 'Password must be at least 6 characters'}), 400
            
            password_hash = hash_password(password)
            
            conn = get_db_connection()
            try:
                user = create_user(conn, email, password_hash, full_name)
                
                if not user:
                    return jsonify({'error': 'Email already registered'}), 409
                
                token = generate_token(user['id'], user['email'], user.get('is_premium', False))
                
                return jsonify({
                    'status': 'success',
                    'token': token,
                    'user': {
                        'id': user['id'],
                        'email': user['email'],
                        'full_name': user.get('full_name'),
                        'is_premium': user.get('is_premium', False)
                    }
                    
                }), 201
                
            finally:
                return_db_connection(conn)
                
        except Exception as e:
            logger.error(f"Signup error: {e}")
            return jsonify({'error': 'Registration failed'}), 500
    
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        """Login a user"""
        try:
            data = request.get_json()
            
            if not data or not data.get('email') or not data.get('password'):
                return jsonify({'error': 'Email and password are required'}), 400
            
            email = data['email'].lower().strip()
            password = data['password']
            
            conn = get_db_connection()
            try:
                user = get_user_by_email(conn, email)
                
                if not user or not verify_password(password, user['password_hash']):
                    return jsonify({'error': 'Invalid email or password'}), 401
                
                token = generate_token(user['id'], user['email'], user.get('is_premium', False))
                
                return jsonify({
                    'status': 'success',
                    'token': token,
                    'user': {
                        'id': user['id'],
                        'email': user['email'],
                        'full_name': user.get('full_name'),
                        'is_premium': user.get('is_premium', False)
                    }
                })
                
            finally:
                return_db_connection(conn)
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return jsonify({'error': 'Login failed'}), 500
    


    @app.route('/api/auth/me', methods=['GET'])
    @token_required
    def get_current_user():
        """Get current user info"""
        try:
            conn = get_db_connection()
            try:
                user = get_user_by_id(conn, request.user_id)
                
                if not user:
                    return jsonify({'error': 'User not found'}), 404
                
                transcript_count = get_user_transcript_count(conn, request.user_id)
                
                return jsonify({
                    'status': 'success',
                    'user': {
                        'id': user['id'],
                        'email': user['email'],
                        'full_name': user.get('full_name'),
                        'is_premium': user.get('is_premium', False),
                        'transcript_count': transcript_count,
                        'transcript_limit': None if user.get('is_premium') else 3
                    }
                })
                
            finally:
                return_db_connection(conn)
                
        except Exception as e:
            logger.error(f"Get user error: {e}")
            return jsonify({'error': 'Failed to get user info'}), 500
    
    @app.route('/api/auth/upgrade', methods=['POST'])
    @token_required
    def upgrade_premium():
        """Upgrade user to premium (₹99)"""
        try:
            conn = get_db_connection()
            try:
                success = upgrade_to_premium(conn, request.user_id)
                
                if not success:
                    return jsonify({'error': 'Upgrade failed'}), 500
                
                user = get_user_by_id(conn, request.user_id)
                token = generate_token(user['id'], user['email'], True)
                
                return jsonify({
                    'status': 'success',
                    'message': 'Successfully upgraded to premium!',
                    'token': token,
                    'user': {
                        'id': user['id'],
                        'email': user['email'],
                        'full_name': user.get('full_name'),
                        'is_premium': True
                    }
                })
                
            finally:
                return_db_connection(conn)
                
        except Exception as e:
            logger.error(f"Upgrade error: {e}")
            return jsonify({'error': 'Upgrade failed'}), 500
    

    @app.route('/api/auth/create_order', methods=['POST'])
    @token_required
    def create_order():
        """Create a new order"""
        try:
            amount = 9900
            currency = "INR"
            order = razorpay_client.order.create({
                "amount": amount,
                "currency": currency,
                "payment_capture": "1",
                "notes": {
                    "user_id": request.user_id,
                    "email": request.user_email,
                    "plan": "premium"
                }
            })
            return jsonify({
                "status": "success",
                "order_id": order["id"],
                "amount": amount,
                "currency": currency,
                "key_id": RAZORPAY_KEY_ID
            })
        except Exception as e:
            logger.error(f"Error create payment: {e}")
            return jsonify({'error': 'Failed to create payment'}), 500

    @app.route('/api/auth/verify_payment', methods=['POST'])
    @token_required
    def verify_payment():
        """Verify payment and upgrade user to premium"""
        data = request.get_json()
        try:
            razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id": data['razorpay_order_id'],
                "razorpay_payment_id": data['razorpay_payment_id'],
                "razorpay_signature": data['razorpay_signature']
            })
            
            logger.info(f"Payment verified successfully for user {request.user_id}")
            
            conn = get_db_connection()
            try:
                success = upgrade_to_premium(conn, request.user_id)
                
                if not success:
                    logger.error(f"Failed to upgrade user {request.user_id} after payment")
                    return jsonify({'error': 'Payment verified but upgrade failed'}), 500
                
                user = get_user_by_id(conn, request.user_id)
                if not user:
                    return jsonify({'error': 'User not found'}), 404
                token = generate_token(user['id'], user['email'], True)
                logger.info(f"User {request.user_id} upgraded to premium successfully")
                
                return jsonify({
                    'status': 'success',
                    'message': 'Payment verified and upgraded to premium!',
                    'token': token,
                    'user': {
                        'id': user['id'],
                        'email': user['email'],
                        'full_name': user.get('full_name'),
                        'is_premium': True
                    }
                })
                
            finally:
                return_db_connection(conn)
            
        except razorpay.errors.SignatureVerificationError as e:
            logger.error(f"Payment signature verification failed: {e}")
            return jsonify({'error': 'Invalid payment signature'}), 400
        except Exception as e:
            logger.error(f"Error verifying payment: {e}")
            return jsonify({'error': 'Failed to verify payment'}), 500
    @app.route('/api/transcripts', methods=['GET'])
    @token_required
    def get_all_transcripts_api():
        """Get all transcripts for the current user"""
        try:
            transcripts = get_all_transcripts(user_id=request.user_id)
            return jsonify({
                'status': 'success',
                'transcripts': transcripts
            })
        except Exception as e:
            logger.error(f"Error fetching transcripts: {e}")
            return jsonify({'error': 'Failed to fetch transcripts'}), 500
    
    @app.route('/api/transcript/<session_id>', methods=['GET'])
    @token_required
    def get_transcript_api(session_id):
        """Get a specific transcript with utterances"""
        try:
            data = get_transcript_from_db(session_id, include_audio=False, user_id=request.user_id)
            if data:
                return jsonify({
                    'status': 'success',
                    'transcript': data['transcript'],
                    'utterances': data['utterances']
                })
            else:
                return jsonify({'error': 'Transcript not found'}), 404
        except Exception as e:
            logger.error(f"Error fetching transcript: {e}")
            return jsonify({'error': 'Failed to fetch transcript'}), 500
    
    @app.route('/api/transcript/<session_id>', methods=['DELETE'])
    @token_required
    def delete_transcript(session_id):
        """Delete a specific transcript"""
        try:
            success = delete_transcript_from_db(session_id, user_id=request.user_id)
            if success:
                return jsonify({'status': 'success', 'message': 'Transcript deleted successfully'})
            else:
                return jsonify({'error': 'Transcript not found or permission denied'}), 404
        except Exception as e:
            logger.error(f"Error deleting transcript: {e}")
            return jsonify({'error': 'Failed to delete transcript'}), 500
    
    @app.route('/api/analyze/<session_id>', methods=['POST'])
    @token_required
    def analyze_transcript_api(session_id):
        """Analyze transcript with Gemini AI"""
        try:
            data = get_transcript_from_db(session_id, include_audio=False)
            if not data:
                return jsonify({'error': 'Transcript not found'}), 404
            
            transcript_text = data['transcript'].get('text', '')
            utterances = data['utterances']
            
            if not transcript_text:
                return jsonify({'error': 'No transcript text available'}), 400
            
            analysis = analyze_transcript(transcript_text, utterances)
            
            return jsonify({
                'status': 'success',
                'analysis': analysis
            })
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            return jsonify({'error': 'AI service not configured'}), 503
        except Exception as e:
            logger.error(f"Error analyzing transcript: {e}")
            return jsonify({'error': 'Failed to analyze transcript'}), 500
    @app.route('/upload', methods=['POST'])
    @token_required
    def upload_file():
        """Upload and process audio file"""
        try:
            conn = get_db_connection()
            try:
                if not can_create_transcript(conn, request.user_id):
                    transcript_count = get_user_transcript_count(conn, request.user_id)
                    return jsonify({
                        'error': 'Transcript limit reached',
                        'message': f'Free users can only store 3 transcripts. You have {transcript_count}/3. Upgrade to premium for unlimited transcripts.',
                        'limit_reached': True,
                        'current_count': transcript_count,
                        'limit': 3
                    }), 403
            finally:
                return_db_connection(conn)
            
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
                audio_mimetype=audio_mimetype,
                user_id=request.user_id
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
        """Extract and return an audio segment"""
        try:
            with SESSION_LOCK:
                processor = AUDIO_SESSIONS.get(session_id, {}).get('processor')
            
            if processor:
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
                audio_data = get_audio_from_db(session_id)
                if not audio_data or not audio_data['audio_data']:
                    return jsonify({'error': 'Session not found and no stored audio'}), 404
                
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
        """Clean up a specific session"""
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

