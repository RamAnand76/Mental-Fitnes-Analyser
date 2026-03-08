import json
import os
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import logging

from app.database import get_db
from app.models import User, WearableData
from app.schemas import WearableDataBase
from app.dependencies import get_current_user

router = APIRouter(
    prefix="/wearables",
    tags=["wearables"]
)

# Configuration for Google Fit API
# These will need to be provided by the user in the .env or directly here for testing
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_PROJECT_ID = os.environ.get("GOOGLE_PROJECT_ID", "mental-fitness-tracker")
REDIRECT_URI = os.environ.get(
    "GOOGLE_REDIRECT_URI", 
    "http://localhost:8000/wearables/auth/google/callback"
)

SCOPES = [
    'https://www.googleapis.com/auth/fitness.activity.read',
    'https://www.googleapis.com/auth/fitness.heart_rate.read'
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Temporary dict to map state to user_id during oauth flow
# In production, use Redis or signed cookies
oauth_states = {}

def get_client_config():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google client credentials not configured. Please see the setup guide.")
        
    return {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "project_id": GOOGLE_PROJECT_ID or "mental-fitness-tracker",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [REDIRECT_URI]
        }
    }


@router.get("/auth/google/login")
async def google_login(current_user: User = Depends(get_current_user)):
    """
    Initiates the Google OAuth 2.0 flow for the currently logged-in user.
    Requires a valid JWT Bearer token.
    """
    try:
        config = get_client_config()
        flow = InstalledAppFlow.from_client_config(config, SCOPES)
        flow.redirect_uri = REDIRECT_URI
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent select_account'
        )
        
        # Save state to link back to the authenticated user and preserve PKCE code_verifier
        oauth_states[state] = {
            "user_id": current_user.id,
            "code_verifier": getattr(flow, 'code_verifier', None)
        }
        
        return {"authorization_url": authorization_url}
        
    except Exception as e:
        logger.error(f"Error starting OAuth flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/google/callback")
async def google_callback(
    state: str,
    db: Session = Depends(get_db),
    code: str = None,
    error: str = None
):
    """
    Handles the callback from Google after user grants permission.
    Exchanges code for tokens and saves them to the User model.
    Also handles the case where the user denies access (error=access_denied).
    """
    # Always clean up the state regardless of success or failure
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter or session expired.")
    
    session_data = oauth_states.pop(state)  # Clean up in all cases

    # Handle user denying the consent screen gracefully
    if error:
        raise HTTPException(status_code=403, detail=f"Google authorization was denied: {error}")

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code from Google.")

    user_id = session_data["user_id"]
    code_verifier = session_data.get("code_verifier")
    
    try:
        config = get_client_config()
        flow = InstalledAppFlow.from_client_config(config, SCOPES, state=state)
        flow.redirect_uri = REDIRECT_URI
        
        if code_verifier:
            flow.code_verifier = code_verifier
            
        # Trade code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Serialize the credentials to store in the database
        creds_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        # Find user and update their google fit token
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
            
        user.google_fit_token = json.dumps(creds_data)
        db.commit()
        
        # Redirect the user back to the frontend dashboard
        return RedirectResponse(url="http://localhost:3000/dashboard")
        
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to authenticate with Google: {str(e)}")


def get_user_credentials(user: User):
    """Retrieve and build Google Credentials object from user DB record"""
    if not user.google_fit_token:
        return None
        
    creds_data = json.loads(user.google_fit_token)
    return Credentials.from_authorized_user_info(creds_data)


@router.post("/sync")
async def sync_wearable_data(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Fetches the last 30 days of data from Google Fit API for the currently logged-in user and stores it.
    Requires a valid JWT Bearer token. Currently pulls: Step Count and Resting Heart Rate.
    """
    from datetime import timedelta
    
    user = current_user  # Use the authenticated user directly
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    creds = get_user_credentials(user)
    if not creds:
        raise HTTPException(status_code=403, detail="Google Fit not connected for this user.")
        
    try:
        # Build the Google Fit API client
        fitness_service = build('fitness', 'v1', credentials=creds)
        
        # Calculate time range: Last 30 days to now
        now = datetime.now()
        start_time = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        START_TIME_MILLIS = int(start_time.timestamp() * 1000)
        END_TIME_MILLIS = int(now.timestamp() * 1000)
        
        # Payload to fetch aggregated steps and heart rate
        aggregate_request = {
            "aggregateBy": [
                {
                    "dataTypeName": "com.google.step_count.delta"
                },
                {
                    "dataTypeName": "com.google.heart_rate.bpm"
                }
            ],
            "bucketByTime": { "durationMillis": 86400000 }, # Group by day (24 hours)
            "startTimeMillis": START_TIME_MILLIS,
            "endTimeMillis": END_TIME_MILLIS
        }
        
        response = fitness_service.users().dataset().aggregate(
            userId='me', body=aggregate_request
        ).execute()
        
        # Clear existing records for this user in the last 30 days to avoid duplicates
        db.query(WearableData).filter(
            WearableData.user_id == user.id,
            WearableData.date >= start_time,
            WearableData.date <= now
        ).delete()
        
        synced_data = []
        today_steps = 0
        today_heart_rate = None
        
        if 'bucket' in response:
            for bucket in response['bucket']:
                bucket_start = int(bucket['startTimeMillis'])
                bucket_date = datetime.fromtimestamp(bucket_start / 1000.0)
                
                steps = 0
                heart_rate_avg = None
                
                dataset = bucket.get('dataset', [])
                for data in dataset:
                    source = data.get('dataSourceId', '')
                    points = data.get('point', [])
                    
                    if not points: continue
                    
                    # Check for step count data
                    if 'step_count' in source:
                        for p in points:
                            vals = p.get('value', [])
                            if vals and 'intVal' in vals[0]:
                                steps += vals[0]['intVal']
                                
                    # Check for heart rate data
                    elif 'heart_rate' in source:
                        for p in points:
                            vals = p.get('value', [])
                            if vals and 'fpVal' in vals[0]:
                                heart_rate_avg = vals[0]['fpVal']
                
                # Only insert if there's actual data
                if steps > 0 or heart_rate_avg is not None:
                    wearable_record = WearableData(
                        user_id=user.id,
                        date=bucket_date,
                        step_count=steps,
                        resting_heart_rate=heart_rate_avg
                    )
                    db.add(wearable_record)
                    
                    synced_data.append({
                        "steps": steps,
                        "heart_rate": heart_rate_avg,
                        "date": bucket_date.isoformat()
                    })
                    
                    # Track latest day data
                    today_steps = steps
                    today_heart_rate = heart_rate_avg
        
        db.commit()
        
        return {
            "message": "Successfully synchronized Google Fit data",
            "data": {
                "steps": today_steps,
                "heart_rate": today_heart_rate,
                "date": now.isoformat()
            },
            "history": synced_data
        }
        
    except Exception as e:
        logger.error(f"Error syncing with Google Fit: {e}")
        # Need to handle Credentials refresh errors here as well in a prod app
        raise HTTPException(status_code=500, detail=f"Failed to fetch fitness data: {str(e)}")
