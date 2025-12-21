from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Token Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Journal Schemas
class JournalBase(BaseModel):
    content: str
    mood_score: Optional[float] = None

class JournalCreate(JournalBase):
    pass

class Journal(JournalBase):
    id: int
    user_id: int
    sentiment_label: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Prediction Schemas
class SurveyResponse(BaseModel):
    """Matches OSMI 2014 dataset columns"""
    Age: int
    Gender: str
    family_history: str
    work_interfere: str
    self_employed: str
    no_employees: str
    remote_work: str
    tech_company: str
    benefits: str
    care_options: str
    wellness_program: str
    seek_help: str
    anonymity: str
    leave: str
    mental_health_consequence: str
    phys_health_consequence: str
    coworkers: str
    supervisor: str
    mental_health_interview: str
    phys_health_interview: str
    mental_vs_physical: str
    obs_consequence: str

class PredictionResponse(BaseModel):
    prediction: str
    confidence: float
    details: dict
