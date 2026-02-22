from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    google_fit_token = Column(Text, nullable=True) # To store serialized oauth token
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    journals = relationship("Journal", back_populates="owner")
    voice_journals = relationship("VoiceJournal", back_populates="owner")
    wearable_data = relationship("WearableData", back_populates="owner")

class Journal(Base):
    __tablename__ = "journals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    mood_score = Column(Float, nullable=True)
    sentiment_label = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner = relationship("User", back_populates="journals")

class VoiceJournal(Base):
    __tablename__ = "voice_journals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    audio_base64 = Column(Text)  # Store base64 encoded audio strings
    transcription = Column(Text, nullable=True)
    pitch_mean = Column(Float, nullable=True)
    speed_rate = Column(Float, nullable=True)
    dominant_emotion = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner = relationship("User", back_populates="voice_journals")

class WearableData(Base):
    __tablename__ = "wearable_data"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime(timezone=True))
    step_count = Column(Integer, default=0)
    resting_heart_rate = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner = relationship("User", back_populates="wearable_data")
