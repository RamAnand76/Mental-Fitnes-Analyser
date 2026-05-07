import pandas as pd
import numpy as np
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

# Maximum number of days a voice record can be shifted to align with a wearable date.
# Gaps larger than this are considered too loose to produce meaningful correlations.
MAX_GAP_DAYS = 3


def _align_voice_to_wearable(df_voice: pd.DataFrame, df_wearables: pd.DataFrame) -> pd.DataFrame:
    """
    Snap each voice record's date to the nearest wearable date.

    For every unique voice date we find the closest wearable date. If the
    gap is within MAX_GAP_DAYS the voice record is re-labelled with that
    wearable date so the subsequent merge always produces a row. Voice
    records whose nearest wearable date is further away than MAX_GAP_DAYS
    are dropped — they are too temporally distant to be meaningful.

    Returns a new df_voice with the 'date' column replaced by the aligned
    wearable date, then re-grouped (averaged) by that date.
    """
    wearable_dates = pd.to_datetime(df_wearables['date'].values)

    def nearest_wearable_date(voice_date):
        voice_ts = pd.Timestamp(voice_date)
        deltas = np.abs((wearable_dates - voice_ts).days)
        idx = int(np.argmin(deltas))
        gap = int(deltas[idx])
        if gap <= MAX_GAP_DAYS:
            return wearable_dates[idx].date()
        return None  # too far — discard

    df_voice = df_voice.copy()
    df_voice['date'] = df_voice['date'].apply(nearest_wearable_date)

    # Drop voice records that had no close-enough wearable date
    df_voice = df_voice.dropna(subset=['date'])

    if df_voice.empty:
        return df_voice

    # Re-group: multiple voice records may now share the same aligned date
    df_voice = df_voice.groupby('date').mean().reset_index()
    return df_voice


@router.get("/correlations")
def get_user_correlations(user_id: int, db: Session = Depends(get_db)):
    """
    Computes Pearson correlations between physical traits (steps, HR) and
    vocal acoustic features (pitch, speed).

    When voice and wearable records don't share exact calendar dates, each
    voice record is snapped to the nearest wearable date (up to MAX_GAP_DAYS).
    This allows correlations to be computed even when the user records voice
    journals and syncs Google Fit on different days.
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

    # Group wearables by date in case of multiple syncs per day
    df_wearables = df_wearables.groupby('date').mean().reset_index()

    df_voice = pd.DataFrame([{
        'date': r.created_at.date(),
        'pitch': r.pitch_mean,
        'speed': r.speed_rate
    } for r in voice_records])

    df_voice = df_voice.groupby('date').mean().reset_index()

    # --- Attempt exact date merge first ---
    merged = pd.merge(df_wearables, df_voice, on='date', how='inner')

    date_alignment_used = False

    if len(merged) < 3:
        # Not enough exact overlaps — align voice dates to nearest wearable dates
        logger.info(
            f"Only {len(merged)} exact date overlaps for user {user_id}. "
            f"Attempting nearest-date alignment (max gap: {MAX_GAP_DAYS} days)."
        )
        df_voice_aligned = _align_voice_to_wearable(df_voice, df_wearables)

        if not df_voice_aligned.empty:
            merged = pd.merge(df_wearables, df_voice_aligned, on='date', how='inner')
            if len(merged) >= 3:
                date_alignment_used = True
                logger.info(f"Date alignment produced {len(merged)} usable pairs for user {user_id}.")

    if len(merged) < 3:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Not enough overlapping data even after date alignment (max gap: {MAX_GAP_DAYS} days). "
                "Try syncing Google Fit and recording voice journals closer together."
            )
        )

    # Calculate Correlation Matrix using Pearson method
    correlation_matrix = merged[['steps', 'heart_rate', 'pitch', 'speed']].corr(method='pearson')

    # Extract specific insights to return to frontend
    insights = []

    if date_alignment_used:
        insights.append(
            f"Note: voice and wearable records were recorded on different days. "
            f"Each voice entry was matched to the nearest Google Fit sync within {MAX_GAP_DAYS} days."
        )

    # Steps vs Pitch correlation
    step_pitch_corr = correlation_matrix.loc['steps', 'pitch']
    if pd.notna(step_pitch_corr):
        if step_pitch_corr > 0.4:
            insights.append("Higher step counts correlate with higher vocal pitch (often indicates higher energy/happiness).")
        elif step_pitch_corr < -0.4:
            insights.append("Higher step counts correlate with lower vocal pitch (often indicates fatigue or calmness).")

    # HR vs Speed correlation
    hr_speed_corr = correlation_matrix.loc['heart_rate', 'speed']
    if pd.notna(hr_speed_corr):
        if hr_speed_corr > 0.5:
            insights.append("Your resting heart rate and speaking speed rise together, indicating potential anxiety or high stress on those days.")
        elif hr_speed_corr < -0.5:
            insights.append("Your speaking speed drops when your heart rate is high, which might indicate exhaustion.")

    # Steps vs Speed correlation
    step_speed_corr = correlation_matrix.loc['steps', 'speed']
    if pd.notna(step_speed_corr):
        if step_speed_corr > 0.5:
            insights.append("On days with more steps, you tend to speak faster — a sign of higher energy levels.")
        elif step_speed_corr < -0.5:
            insights.append("On days with more steps, your speaking pace slows — possibly reflecting calm post-exercise recovery.")

    # HR vs Pitch correlation
    hr_pitch_corr = correlation_matrix.loc['heart_rate', 'pitch']
    if pd.notna(hr_pitch_corr):
        if hr_pitch_corr > 0.5:
            insights.append("Higher resting heart rate correlates with higher vocal pitch, which may reflect elevated stress or excitement.")
        elif hr_pitch_corr < -0.5:
            insights.append("Lower resting heart rate correlates with higher vocal pitch — a pattern sometimes seen in relaxed, energetic states.")

    # Format the correlation matrix for JSON output — replace NaNs with None
    corr_dict = correlation_matrix.where(pd.notnull(correlation_matrix), None).to_dict()

    return {
        "message": "Correlation computed successfully",
        "data_points_analyzed": len(merged),
        "date_alignment_used": date_alignment_used,
        "max_gap_days": MAX_GAP_DAYS,
        "correlation_matrix": corr_dict,
        "ai_insights": insights if insights else ["Keep logging more data to uncover deeper patterns between your physical activity and vocal acoustics!"]
    }
