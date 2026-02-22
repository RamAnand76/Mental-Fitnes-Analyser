import os
import shutil
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

import librosa
import numpy as np
import soundfile as sf
import base64
import whisper
from transformers import pipeline

from app.database import get_db
from app.models import User, VoiceJournal
from app import schemas

router = APIRouter(
    prefix="/voice",
    tags=["voice_journal"]
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure uploads directory exists
UPLOAD_DIR = Path("uploads/audio")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# We use global variables to load pipelines once during startup to avoid latency
emotion_classifier = None
whisper_model = None

TARGET_SR = 16000  # Standard sample rate for speech models

def get_whisper_model():
    """Lazy load the Whisper tiny model for transcription"""
    global whisper_model
    if whisper_model is None:
        logger.info("Loading Whisper transcription model...")
        try:
            whisper_model = whisper.load_model("tiny")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
    return whisper_model


def get_emotion_classifier():
    """Lazy load the HuggingFace audio emotion classification pipeline"""
    global emotion_classifier
    if emotion_classifier is None:
        logger.info("Loading HuggingFace Audio Emotion model...")
        try:
            emotion_classifier = pipeline(
                "audio-classification",
                model="superb/hubert-base-superb-er"
            )
        except Exception as e:
            logger.error(f"Failed to load HuggingFace pipeline: {e}")
            raise HTTPException(status_code=500, detail="Audio AI model unavailable.")

    return emotion_classifier


def load_audio_as_array(file_path: str):
    """
    Load an audio file into a numpy array using soundfile.
    This does NOT require FFmpeg — it uses libsndfile which is bundled with soundfile.
    Supports: WAV, FLAC, OGG (Vorbis). For MP3, we convert to WAV first using pydub as fallback.
    """
    ext = Path(file_path).suffix.lower()

    if ext in ['.wav', '.flac', '.ogg']:
        # soundfile can handle these natively without ffmpeg
        data, sr = sf.read(file_path, dtype='float32')
        # Convert stereo to mono if needed
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        return data, sr

    elif ext in ['.mp3', '.m4a']:
        # For MP3/M4A: try pydub (which bundles its own ffmpeg via ffmpeg-python or simpleaudio)
        # If pydub fails, give user a clear error
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(file_path)
            audio = audio.set_channels(1)  # mono
            audio = audio.set_frame_rate(TARGET_SR)
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            samples = samples / (2**15)  # Normalize int16 to float32
            return samples, TARGET_SR
        except Exception as e:
            logger.error(f"Cannot decode {ext} file: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Cannot process {ext} files. Please upload a .wav file, or install FFmpeg on your system for MP3/M4A support."
            )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: {ext}")


def analyze_acoustics(audio_data: np.ndarray, sr: int):
    """
    Extract pitch (F0) and speaking rate (tempo) using Librosa.
    Accepts raw numpy arrays so FFmpeg is never needed.
    """
    try:
        # Resample if needed for consistency
        if sr != TARGET_SR:
            audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=TARGET_SR)
            sr = TARGET_SR

        # 1. Pitch / Fundamental Frequency (F0) using PYIN
        f0, voiced_flag, voiced_probs = librosa.pyin(
            audio_data,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C7'),
            sr=sr
        )
        valid_f0 = f0[~np.isnan(f0)]
        pitch_mean = float(np.mean(valid_f0)) if len(valid_f0) > 0 else 0.0

        # 2. Speaking Rate (Approximated via onset tempo)
        onset_env = librosa.onset.onset_strength(y=audio_data, sr=sr)
        tempo = librosa.feature.tempo(onset_envelope=onset_env, sr=sr)
        speed_rate = float(tempo[0]) if len(tempo) > 0 else 0.0

        return pitch_mean, speed_rate
    except Exception as e:
        logger.error(f"Acoustic analysis failed: {e}")
        return 0.0, 0.0


@router.post("/upload")
async def upload_voice_journal(
    user_id: int,
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a voice recording. The system will:
    1. Save the file.
    2. Extract acoustic features (pitch, speed) via librosa.
    3. Analyze emotion via HuggingFace transformers.
    4. Save insights to DB.
    """
    # 1. Validate User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Save the file
    file_ext = Path(audio_file.filename).suffix
    if file_ext.lower() not in ['.wav', '.mp3', '.m4a', '.ogg', '.flac']:
        raise HTTPException(status_code=400, detail="Invalid audio format. Supported: WAV, MP3, M4A, OGG, FLAC.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"user_{user.id}_{timestamp}{file_ext}"
    file_path = UPLOAD_DIR / safe_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(audio_file.file, buffer)

    try:
        # 3. Load audio into numpy array (NO FFmpeg needed for WAV)
        logger.info(f"Loading audio for {safe_filename}...")
        audio_data, sr = load_audio_as_array(str(file_path))

        # 4. Analyze Acoustics (Pitch, Speed)
        logger.info(f"Analyzing acoustics for {safe_filename}...")
        pitch, speed = analyze_acoustics(audio_data, sr)

        # 5. Predict Emotion directly from raw audio array
        logger.info(f"Predicting emotion for {safe_filename}...")
        classifier = get_emotion_classifier()

        # Resample to 16kHz for the HF model (it expects 16kHz)
        if sr != TARGET_SR:
            audio_16k = librosa.resample(audio_data, orig_sr=sr, target_sr=TARGET_SR)
        else:
            audio_16k = audio_data

        # Pass raw numpy array + sampling rate directly to the pipeline
        predictions = classifier({"raw": audio_16k, "sampling_rate": TARGET_SR})

        # The pipeline returns a list of dicts like: [{'score': 0.9, 'label': 'happy'}, ...]
        predictions.sort(key=lambda x: x['score'], reverse=True)
        dominant_emotion = predictions[0]['label'] if predictions else "unknown"

        # --- NEW: Whisper Transcription ---
        logger.info(f"Transcribing audio for {safe_filename}...")
        w_model = get_whisper_model()
        transcription_text = "Transcription unavailable."
        
        if w_model:
            # Whisper can accept the file path directly or a normalized numpy array 
            # (must be float32, 16kHz, mono - which audio_16k is)
            result = w_model.transcribe(audio_16k)
            transcription_text = result.get("text", "").strip()

        # --- NEW: Base64 Encoding ---
        # Instead of saving the path, we encode the completely raw bytes to base64
        with open(file_path, "rb") as audio_binary:
            encoded_bytes = base64.b64encode(audio_binary.read())
            base64_string = encoded_bytes.decode('utf-8')

        # 6. Save to DB
        journal_entry = VoiceJournal(
            user_id=user.id,
            audio_base64=base64_string,
            pitch_mean=pitch,
            speed_rate=speed,
            dominant_emotion=dominant_emotion,
            transcription=transcription_text
        )

        db.add(journal_entry)
        db.commit()
        db.refresh(journal_entry)

        return {
            "message": "Voice journal analyzed successfully",
            "insights": {
                "journal_id": journal_entry.id,
                "emotion": dominant_emotion,
                "confidence": round(predictions[0]['score'], 4) if predictions else 0.0,
                "acoustics": {
                    "average_pitch_hz": round(pitch, 2),
                    "speaking_speed_bpm": round(speed, 2)
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice processing pipeline error: {e}", exc_info=True)
        # Clean up file on failure
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to process audio: {str(e)}")
    finally:
        # ALWAYS clean up the temporary file, success or failure
        if file_path.exists():
            file_path.unlink()


@router.get("/journals", response_model=list[schemas.VoiceJournal])
def get_voice_journals(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieve all voice journal entries for a user, including the base64 audio and extracted features.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    journals = db.query(VoiceJournal).filter(VoiceJournal.user_id == user.id).order_by(VoiceJournal.created_at.desc()).all()
    return journals
