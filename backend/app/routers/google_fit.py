import json
import os
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import logging

from app.database import get_db
from app.models import User, WearableData
from app.schemas import WearableDataBase

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
async def google_login(user_id: int):
    """
    Initiates the Google OAuth 2.0 flow for a specific user to connecting their Fit account.
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
        
        # Save state to link back to the user
        oauth_states[state] = user_id
        
        return {"authorization_url": authorization_url}
        
    except Exception as e:
        logger.error(f"Error starting OAuth flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/google/callback")
async def google_callback(state: str, code: str, db: Session = Depends(get_db)):
    """
    Handles the callback from Google after user grants permission.
    Exchanges code for tokens and saves them to the User model.
    """
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter or session expired.")
    
    user_id = oauth_states.pop(state)
    
    try:
        config = get_client_config()
        flow = InstalledAppFlow.from_client_config(config, SCOPES, state=state)
        flow.redirect_uri = REDIRECT_URI
        
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
        
        return {"message": "Google Fit successfully connected!", "user_id": user_id}
        
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
async def sync_wearable_data(user_id: int, db: Session = Depends(get_db)):
    """
    Fetches the latest data from Google Fit API for the given user and stores it.
    Currently pulls: Step Count and Resting Heart Rate.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    creds = get_user_credentials(user)
    if not creds:
        raise HTTPException(status_code=403, detail="Google Fit not connected for this user.")
        
    try:
        # Build the Google Fit API client
        fitness_service = build('fitness', 'v1', credentials=creds)
        
        # Calculate time range: Today, midnight to current time
        now = datetime.now()
        startOfDay = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        START_TIME_MILLIS = int(startOfDay.timestamp() * 1000)
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
        
        # Parse response
        steps = 0
        heart_rate_avg = None
        
        if 'bucket' in response and len(response['bucket']) > 0:
            dataset = response['bucket'][0].get('dataset', [])
            
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
                            # Getting an average mapping for the bucket
                            # Google frequently returns fpVal for floats
                            heart_rate_avg = vals[0]['fpVal']
        
        # Save to database
        wearable_record = WearableData(
            user_id=user.id,
            date=now,
            step_count=steps,
            resting_heart_rate=heart_rate_avg
        )
        db.add(wearable_record)
        db.commit()
        db.refresh(wearable_record)
        
        return {
            "message": "Successfully synchronized Google Fit data",
            "data": {
                "steps": steps,
                "heart_rate": heart_rate_avg,
                "date": now.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error syncing with Google Fit: {e}")
        # Need to handle Credentials refresh errors here as well in a prod app
        raise HTTPException(status_code=500, detail=f"Failed to fetch fitness data: {str(e)}")
