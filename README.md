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
- **PostgreSQL** - Local or cloud
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
```

---

## License

This project is licensed under the MIT License.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/Shubhwtf/speaker_recogn/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Shubhwtf/speaker_recogn/discussions)

<div align="center">

[Report Bug](https://github.com/Shubhwtf/speaker_recogn/issues) · [Request Feature](https://github.com/Shubhwtf/speaker_recogn/issues)

</div>