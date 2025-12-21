from fastapi import APIRouter, HTTPException, Depends
import pandas as pd
import joblib
import logging
from app import schemas

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Prediction"]
)

# Global variables for model and encoders
model = None
encoders = None

def load_prediction_models():
    """Load ML models and encoders"""
    global model, encoders
    try:
        logger.info("Loading model artifacts...")
        # Path assumes we are running from backend/ root
        model = joblib.load('mental_health_osmi_model.pkl')
        encoders = joblib.load('osmi_encoders.pkl')
        logger.info("✅ Model and encoders loaded successfully")
    except Exception as e:
        logger.error(f"❌ Error loading models: {e}")
        # We don't exit here to allow app to start even if model fails, 
        # but endpoints will fail. Ideally handle better.

@router.post("/predict", response_model=schemas.PredictionResponse)
async def predict_mental_health(survey: schemas.SurveyResponse):
    if model is None or encoders is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Step 1: Convert Pydantic model to DataFrame
        input_dict = survey.dict()
        input_df = pd.DataFrame([input_dict])
        
        # Step 2: Handle Gender normalization (logic adapted from original)
        # Assuming the input schema allows raw strings, we normalize here or relying on frontend/schema.
        # The schema definition helps validation.
        # Original logic had a validator in Pydantic. Pydantic v2 moved validators.
        # For simplicity, we assume generic 'Gender' input and apply normalization if needed, 
        # or rely on the encoders handling it (if they were trained on normalized data).
        # original main.py had normalization logic in `UserResponse` validator.
        # I omitted complex validator for brevity but let's replicate basic normalization if essential.
        
        gender = input_dict.get('Gender', '').lower().strip()
        if gender in ['male', 'm', 'man', 'cis male', 'male-ish', 'maile', 'mal', 'male (cis)', 'make', 'male ', 'msle']:
            input_df['Gender'] = 'Male'
        elif gender in ['female', 'f', 'woman', 'femake', 'female ', 'cis female', 'femail']:
            input_df['Gender'] = 'Female'
        else:
            input_df['Gender'] = 'Other'

        # Step 3: Encode features
        for col, encoder in encoders.items():
            if col in input_df.columns:
                try:
                    original_value = input_df[col].iloc[0]
                    # Handle unseen labels by defaulting to 0 or mode if possible, or try/except
                    # transform expects 2D array or list
                    input_df[col] = encoder.transform([original_value])
                except ValueError:
                    # Unseen label
                    input_df[col] = 0
        
        # Step 4: Reorder columns
        if hasattr(model, 'feature_names_in_'):
            expected_features = list(model.feature_names_in_)
            # Add missing with 0
            for col in expected_features:
                if col not in input_df.columns:
                    input_df[col] = 0
            input_df = input_df[expected_features]
            
        # Step 5: Predict
        prediction = model.predict(input_df)
        probability = model.predict_proba(input_df)
        
        prediction_label = "Treatment Needed" if prediction[0] == 1 else "No Treatment Needed"
        confidence_score = float(probability[0][prediction[0]] * 100)
        
        return {
            "prediction": prediction_label,
            "confidence": round(confidence_score, 2),
            "details": {
                "prediction_class": int(prediction[0]),
                "recommendation": "Consult professional" if prediction[0] == 1 else "Monitor health"
            }
        }
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
