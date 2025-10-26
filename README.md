# AI Speaker Recognition Platform

<div align="center">

A powerful, AI-driven speaker recognition and transcription platform with advanced sentiment analysis, built with React and Flask.

[![React](https://img.shields.io/badge/React-19.1.1-61DAFB?logo=react)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Latest-4169E1?logo=postgresql)](https://www.postgresql.org/)
</div>

---

## Features

### Core Features
- **Multi-Speaker Recognition** - Automatically identifies and separates different speakers in audio recordings
- **Real-time Transcription** - Powered by AssemblyAI for accurate speech-to-text conversion
- **AI-Powered Insights** - Leverages Google Gemini 2.5 Flash for comprehensive summaries, sentiment analysis, key takeaway extraction, and topic identification
- **Timestamp Playback** - Click any utterance to play audio from that specific moment
- **Confidence Scores** - View transcription confidence for each speaker segment
- **Audio Format Support** - Supports MP3, WAV, M4A, FLAC, and OGG formats

### User Features
- **JWT Authentication** - Secure user registration and login
- **Premium Tier System** - Free users get 3 transcripts, premium users get unlimited transcripts for ₹99
- **Razorpay Integration** - Seamless payment processing for premium upgrades
- **Transcript History** - Access and manage all your past transcriptions
- **Session Management** - Automatic cleanup of expired sessions

### User Interface
- **Modern Black & White Theme** - Clean, professional design
- **Responsive Layout** - Works seamlessly on desktop and mobile
- **Smooth Animations** - Powered by Framer Motion
- **Interactive Audio Player** - Play/pause controls for each utterance
- **Real-time Feedback** - Loading states and progress indicators

---

## Tech Stack

### Frontend
- **React 19** - Modern UI library with latest features
- **Vite** - Lightning-fast build tool and dev server
- **Framer Motion** - Smooth animations and transitions
- **Lucide React** - Beautiful, consistent icon set

### Backend
- **Flask 3.0** - Lightweight Python web framework
- **PostgreSQL** - Robust relational database (NeonDB compatible)
- **AssemblyAI** - Industry-leading speech recognition API
- **Google Gemini 2.5 Flash** - Advanced AI model for text analysis
- **PyJWT** - JSON Web Token implementation
- **Bcrypt** - Secure password hashing
- **Razorpay** - Payment gateway integration
- **Pydub** - Audio file processing

---

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.13+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **PostgreSQL** - Local or cloud (NeonDB recommended) - [NeonDB](https://neon.tech/)
- **Git** - [Download](https://git-scm.com/)

### Required API Keys

You'll need to sign up for the following services:

1. **AssemblyAI** - [Get API Key](https://www.assemblyai.com/)
2. **Google Gemini** - [Get API Key](https://ai.google.dev/)
3. **Razorpay** - [Get API Key](https://razorpay.com/) (for premium payments)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Shubhwtf/speaker_recogn.git
cd speaker_recogn
```

### 2. Backend Setup

```bash
cd speaker_recogn
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cat > .env << EOF
# AssemblyAI Configuration
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
# Database Configuration (NeonDB or local PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/database
# Google Gemini API Configuration
GOOGLE_API_KEY=your_google_gemini_api_key_here
# Flask Configuration
PORT=8000
FLASK_DEBUG=false
# JWT Secret (IMPORTANT: Change this to a random 32+ character string)
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production-min-32-chars
# Razorpay Configuration
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_secret
EOF
# Initialize database
python db_setup.py
# Start the backend server
python app.py
```

The backend will start on `http://localhost:8000`

### 3. Frontend Setup

Open a new terminal:

```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev
```

The frontend will start on `http://localhost:5173`

---

## Environment Variables

### Backend (.env in `speaker_recogn/`)

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `ASSEMBLYAI_API_KEY` | AssemblyAI API key for transcription | Yes | `abc123...` |
| `DATABASE_URL` | PostgreSQL connection string | Yes | `postgresql://user:pass@host/db` |
| `GOOGLE_API_KEY` | Google Gemini API key | Yes | `xyz789...` |
| `JWT_SECRET` | Secret key for JWT tokens (32+ chars) | Yes | `your-secret-key-here` |
| `RAZORPAY_KEY_ID` | Razorpay key ID for payments | Yes | `rzp_test_...` |
| `RAZORPAY_KEY_SECRET` | Razorpay secret key | Yes | `secret123...` |
| `PORT` | Backend server port | No | `8000` (default) |
| `FLASK_DEBUG` | Enable debug mode | No | `false` (default) |

### Frontend (.env in `frontend/`)

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `VITE_API_URL` | Backend API URL | Yes | `http://localhost:8000` |

---

## Usage

### For Users

1. **Sign Up / Login**
   - Create a new account or login with existing credentials
   - Free users get 3 transcripts

2. **Upload Audio**
   - Click "Upload Audio" on the home page
   - Select an audio file (MP3, WAV, M4A, FLAC, OGG)
   - Wait for transcription to complete

3. **View Results**
   - See speaker breakdown with confidence scores
   - Read AI-generated summary and key points
   - Check overall sentiment analysis
   - Click any utterance to play audio from that timestamp

4. **Manage Transcripts**
   - Access "History" to view all transcripts
   - Click any transcript to see details
   - Download or delete transcripts as needed

5. **Upgrade to Premium**
   - Click "Upgrade to Premium" button
   - Pay ₹99 via Razorpay (UPI, Cards, Net Banking)
   - Get unlimited transcripts instantly

### For Developers

#### Run Backend Tests
```bash
cd speaker_recogn
python db_setup.py test
```

#### Build Frontend for Production
```bash
cd frontend
npm run build
# Output will be in dist/
```

#### Lint Frontend Code
```bash
cd frontend
npm run lint
```

---

## Project Structure

```
speaker_recogn/
├── frontend/                  # React frontend application
│   ├── src/
│   │   ├── components/       # React components
│   │   │   ├── Auth.jsx      # Authentication UI
│   │   │   ├── AudioUpload.jsx       # Audio upload interface
│   │   │   ├── PastTranscripts.jsx   # Transcript history
│   │   │   ├── TranscriptResults.jsx # Results display
│   │   │   └── PremiumUpgrade.jsx    # Premium payment modal
│   │   ├── context/          # React Context API
│   │   │   └── AuthContext.jsx       # Authentication state
│   │   ├── App.jsx           # Main app component
│   │   ├── main.jsx          # Entry point
│   │   └── index.css         # Global styles
│   ├── package.json          # NPM dependencies
│   └── vite.config.js        # Vite configuration
│
├── speaker_recogn/           # Flask backend application
│   ├── app.py                # Flask app entry point
│   ├── config.py             # Configuration and constants
│   ├── api_routes.py         # API endpoint handlers
│   ├── database.py           # Database connection & queries
│   ├── db_setup.py           # Database initialization
│   ├── audio_processor.py    # Audio processing logic
│   ├── gemini_service.py     # Google Gemini AI integration
│   ├── auth_service.py       # JWT authentication
│   ├── user_db.py            # User database operations
│   └── requirements.txt      # Python dependencies
│
└── README.md                 # This file
```

---

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/signup` | Register new user | No |
| POST | `/api/auth/login` | Login user | No |
| GET | `/api/auth/me` | Get current user | Yes |
| POST | `/api/auth/create_order` | Create Razorpay order | Yes |
| POST | `/api/auth/verify_payment` | Verify payment & upgrade | Yes |

### Transcripts

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/upload` | Upload audio for transcription | Yes |
| GET | `/api/transcripts` | Get all user transcripts | Yes |
| GET | `/api/transcript/<id>` | Get specific transcript | Yes |
| DELETE | `/api/transcript/<id>` | Delete transcript | Yes |
| POST | `/api/analyze/<id>` | Generate AI insights | Yes |
| GET | `/audio_segment/<id>/<start>/<end>` | Get audio segment | Yes |

### System

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | API information | No |

---

## Security Features

- **JWT Authentication** - Secure token-based authentication
- **Bcrypt Password Hashing** - Industry-standard password security
- **CORS Protection** - Configured for frontend-backend communication
- **Secure Payments** - Razorpay signature verification
- **SSL/TLS** - Database connections use SSL in production
- **Token Expiration** - 24-hour token expiry for security
- **SQL Injection Prevention** - Parameterized queries
- **Rate Limiting** - Session cleanup prevents resource exhaustion

---


### Typography
- **Font**: System UI fonts for optimal performance
- **Sizes**: Responsive scaling from mobile to desktop

### Animations
- **Smooth transitions** via Framer Motion
- **Stagger animations** for lists
- **Micro-interactions** for better UX

---

## Troubleshooting

### Common Issues

**1. `ModuleNotFoundError: No module named 'audioop'`**
- **Solution**: Install `audioop-lts` for Python 3.13+
  ```bash
  pip install audioop-lts
  ```

**2. PostgreSQL SSL Connection Error**
- **Solution**: Check `sslmode` in database connection
  - Local: `sslmode=prefer`
  - NeonDB: `sslmode=require`

**3. CORS Errors**
- **Solution**: Ensure `VITE_API_URL` in frontend `.env` matches backend URL

**4. Payment Not Redirecting (Firefox)**
- **Solution**: Already fixed with `window.location.replace()`

**5. Database Connection Failed**
- **Solution**: Verify `DATABASE_URL` format:
  ```
  postgresql://username:password@host:port/database?sslmode=require
  ```

---

## Performance Optimization

### Backend
- Connection pooling for database
- Session cleanup for expired data
- Gunicorn for production serving
- Efficient audio segment streaming

### Frontend
- Vite for fast builds and HMR
- Code splitting and lazy loading
- Optimized animations with Framer Motion
- Debounced API calls

---

## Authors

- **Shubham** - [@Shubhwtf](https://github.com/Shubhwtf)

---

## Acknowledgments

- **AssemblyAI** - For excellent speech recognition API
- **Google Gemini** - For powerful AI text analysis
- **Razorpay** - For seamless payment integration
- **NeonDB** - For serverless PostgreSQL hosting
- **React & Flask Communities** - For amazing documentation and support

---

## Support

- **Issues**: [GitHub Issues](https://github.com/Shubhwtf/speaker_recogn/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Shubhwtf/speaker_recogn/discussions)
- **Email**: shubhampawar007.gp@gmail.com

<div align="center">

Star this repo if you find it helpful!

[Report Bug](https://github.com/Shubhwtf/speaker_recogn/issues) · [Request Feature](https://github.com/Shubhwtf/speaker_recogn/issues)

</div>