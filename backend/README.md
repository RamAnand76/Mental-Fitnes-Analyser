# Mental Health Tracker API - Backend

This backend API analyzes mental fitness, tracks user moods, and provides AI-powered insights. It is a comprehensive mental health platform built for modern needs.

## 🌟 Key Features

1.  **Mental Health Prediction (ML)**
    *   Uses a **Random Forest Classifier** to analyze survey data (OSMI 2014) and predict if a user needs professional treatment.
    *   Reach: 80%+ Accuracy.

2.  **Smart Journaling (NLP)**
    *   Private, secure journals for users.
    *   **Auto-Sentiment Analysis**: Uses **VADER** (Valence Aware Dictionary and sEntiment Reasoner) to automatically score every entry as Positive, Negative, or Neutral.
    *   Tracks mood trends over time.

3.  **AI Insights (LLM)**
    *   Powered by **Google Gemini AI**.
    *   Generates personalized Weekly/Monthly wellness reports based on your journal history.
    *   Provides actionable advice and summarizes recurring themes in your life.

4.  **Voice Journaling (Acoustic, Emotion & Speech AI)**
    *   Secure audio journal uploads using **librosa** for acoustic parsing (pitch and speed).
    *   **Emotion Detection**: Uses locally hosted **HuggingFace Transformers** to identify emotional undertones in your speech.
    *   **Transcription**: Integrates **OpenAI Whisper (Tiny)** to automatically transcribe your voice audio into full text formats locally.
    *   **Base64 Storage Engine**: Audio files are not stored on the disk; instead, they are converted into pure **Base64** text strings and injected directly into the SQLite/PostgreSQL Database for highly portable JSON transit.

5.  **Wearable Syncing & Correlation**
    *   Secure **Google Fit API** connectivity.
    *   Correlates historical physical signals (Step Count, Heart Rate) directly against your mood and vocal traits using Pandas Pearson Correlation algorithms to uncover unique insights.

6.  **Secure Authentication**
    *   Full user management (Signup/Login).
    *   **JWT (JSON Web Tokens)** for stateless, secure API access.
    *   Password hashing using **Bcrypt**.

---

## 🛠️ Tech Stack

*   **Framework**: FastAPI (Python)
*   **Database**: PostgreSQL / SQLite (via SQLAlchemy ORM)
*   **Authentication**: OAuth2 with JWT & Google OAuth 2.0 (Wearables)
*   **Machine Learning**: Scikit-Learn (Random Forest)
*   **NLP & Audio Processing**: VADER Sentiment Analysis, Librosa, HuggingFace Transformers, OpenAI Whisper (Speech-to-Text)
*   **Data Science**: Pandas (Correlation Matrix)
*   **Generative AI**: Google Gemini Pro

---

## 🚀 Setup Guide

### 1. Prerequisites
*   Python 3.9+
*   PostgreSQL (Local or Docker)

### 2. Installation

```bash
# Clone and enter directory
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration (.env)
Create a `.env` file in the `backend/` folder:

```env
# Database Credentials
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mental_health

# Security
SECRET_KEY=your_super_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Configuration
GEMINI_API_KEY=your_gemini_api_key_from_google_ai_studio
```

### 4. Database Setup
The application automatically creates tables on startup. Just ensure the database (e.g., `mental_health`) exists in Postgres.

```sql
CREATE DATABASE mental_health;
```

### 5. Run Server
```bash
uvicorn app.main:app --reload
```
Open **[http://localhost:8000/docs](http://localhost:8000/docs)** for the interactive API documentation.

---

## 📡 API Endpoints

### Authentication
*   `POST /auth/signup`: Register a new user.
*   `POST /auth/login`: Login to get Access & Refresh Tokens.
*   `POST /auth/refresh`: Get a new access token.

### Journals
*   `POST /journals/`: Add a daily entry (Auto-Analysis runs here).
*   `GET /journals/`: View all entries.
*   `GET /journals/insights/report`: **Get AI-generated Weekly/Monthly Report.**

### Prediction
*   `POST /predict`: Submit survey responses to get a Treatment recommendation.

### Voice & Wearables
*   `POST /voice/upload`: Upload an audio file (.wav, .mp3, .m4a, .ogg) for acoustic, emotion, and text transcription analysis. Audio data is serialized to Base64.
*   `GET /voice/journals`: Fetch all historical audio recordings for a user, returned seamlessly in JSON via the Base64 strings.
*   `GET /wearables/auth/google/login`: Initiates the Google Fit OAuth 2.0 flow for syncing data.
*   `POST /wearables/sync`: Pull latest steps and heart rate from connected Google accounts.
*   `GET /insights/correlations`: Generate Pearson correlations between physical stats and voice metrics to uncover insights.
---

## 🧠 AI Models Explained

### 1. Random Forest (Treatment Prediction)
An ensemble learning method that uses multiple Decision Trees to determine if a user needs mental health treatment based on workplace and personal factors.

### 2. VADER (Mood Analysis)
A rule-based sentiment analysis tool specifically tuned for social media. It understands intensity ("really happy"), capitalization ("SAD"), and emojis, converting text into a numeric Mood Score (-1.0 to +1.0).

### 3. Google Gemini (Wellness Reports)
A Large Language Model (LLM) that reads your recent journal entries and synthesizes them into a coherent, empathetic summary with actionable mental health advice.

### 4. OpenAI Whisper (Speech Transcription)
A highly resilient, open-source automatic speech recognition (ASR) system. Implemented directly in Python (using the local lightweight `tiny` model) to accurately transcribe user audio diaries into text.
