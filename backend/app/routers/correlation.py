import pandas as pd
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
import logging

from app.database import get_db
from app.models import User, WearableData, VoiceJournal

router = APIRouter(
    prefix="/insights",
    tags=["insights"]
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.get("/correlations")
def get_user_correlations(user_id: int, db: Session = Depends(get_db)):
    """
    Computes mathematical correlations between Physical traits (steps, HR) 
    and Emotional traits (vocal pitch, speed, mood score) over time using Pandas.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Fetch Data
    wearable_records = db.query(WearableData).filter(WearableData.user_id == user_id).all()
    voice_records = db.query(VoiceJournal).filter(VoiceJournal.user_id == user_id).all()
    
    if len(wearable_records) < 3 or len(voice_records) < 3:
        raise HTTPException(
            status_code=400, 
            detail="Not enough data to calculate meaningful correlations. Keep logging!"
        )
        
    # Build Pandas DataFrames
    df_wearables = pd.DataFrame([{
        'date': r.date.date(),
        'steps': r.step_count,
        'heart_rate': r.resting_heart_rate
    } for r in wearable_records])
    
    # We group wearables by date in case of multiple syncs per day
    df_wearables = df_wearables.groupby('date').mean().reset_index()
    
    df_voice = pd.DataFrame([{
        'date': r.created_at.date(),
        'pitch': r.pitch_mean,
        'speed': r.speed_rate
    } for r in voice_records])
    
    df_voice = df_voice.groupby('date').mean().reset_index()
    
    # Merge on Date to find days where we have BOTH physical and voice data
    merged = pd.merge(df_wearables, df_voice, on='date', how='inner')
    
    if len(merged) < 3:
        raise HTTPException(
            status_code=400,
            detail="Correlation requires overlapping days of both Wearable syncs and Voice journals. Keep logging!"
        )
        
    # Calculate Correlation Matrix using Pearson method
    correlation_matrix = merged[['steps', 'heart_rate', 'pitch', 'speed']].corr(method='pearson')
    
    # Extract specific insights to return to frontend
    insights = []
    
    # Step vs Pitch correlation
    step_pitch_corr = correlation_matrix.loc['steps', 'pitch']
    if pd.notna(step_pitch_corr):
        step_pitch_str = "moderate" if abs(step_pitch_corr) > 0.4 else "weak"
        if step_pitch_corr > 0.4:
            insights.append("Higher step counts correlate strongly with higher vocal pitch (often indicates higher energy/happiness).")
        elif step_pitch_corr < -0.4:
            insights.append("Higher step counts correlate with lower vocal pitch (often indicates fatigue or calmness).")
            
    # HR vs Speed correlation
    hr_speed_corr = correlation_matrix.loc['heart_rate', 'speed']
    if pd.notna(hr_speed_corr):
        if hr_speed_corr > 0.5:
            insights.append("Your resting heart rate and speaking speed rise together, indicating potential anxiety or high stress on those days.")
        elif hr_speed_corr < -0.5:
            insights.append("Your speaking speed drops when your heart rate is high, which might indicate exhaustion.")
            
    # Format the correlation matrix for raw JSON output
    # Replace NaNs with None for JSON serialization
    corr_dict = correlation_matrix.where(pd.notnull(correlation_matrix), None).to_dict()
    
    return {
        "message": "Correlation computed successfully",
        "data_points_analyzed": len(merged),
        "correlation_matrix": corr_dict,
        "ai_insights": insights if insights else ["Keep logging more data to uncover deeper patterns between your physical activity and vocal acoustics!"]
    }
