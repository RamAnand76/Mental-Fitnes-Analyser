"""
Mental Health Tracker API
FastAPI backend for predicting mental health treatment needs using Random Forest model
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import pandas as pd
import joblib
import logging
from typing import Dict, Any
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Mental Health Tracker API",
    description="API for predicting mental health treatment needs based on OSMI 2014 dataset",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for model and encoders
model = None
encoders = None


class UserResponse(BaseModel):
    """
    Pydantic model for user input validation.
    Matches OSMI 2014 dataset columns.
    """
    Age: int = Field(..., ge=18, le=100, description="User's age (18-100)")
    Gender: str = Field(..., description="Gender (Male/Female/Other)")
    family_history: str = Field(..., description="Family history of mental illness (Yes/No)")
    work_interfere: str = Field(..., description="Work interference level (Often/Rarely/Never/Sometimes/Unknown)")
    self_employed: str = Field(..., description="Self-employment status (Yes/No)")
    no_employees: str = Field(..., description="Company size (1-5/6-25/26-100/100-500/500-1000/More than 1000)")
    remote_work: str = Field(..., description="Remote work status (Yes/No)")
    tech_company: str = Field(..., description="Tech company (Yes/No)")
    benefits: str = Field(..., description="Mental health benefits (Yes/No/Don't know)")
    care_options: str = Field(..., description="Knowledge of care options (Yes/No/Not sure)")
    wellness_program: str = Field(..., description="Wellness program discussed (Yes/No/Don't know)")
    seek_help: str = Field(..., description="Resources to learn about mental health (Yes/No/Don't know)")
    anonymity: str = Field(..., description="Anonymity protection (Yes/No/Don't know)")
    leave: str = Field(..., description="Ease of taking leave (Very easy/Somewhat easy/Somewhat difficult/Very difficult/Don't know)")
    mental_health_consequence: str = Field(..., description="Mental health discussion consequences (Yes/No/Maybe)")
    phys_health_consequence: str = Field(..., description="Physical health discussion consequences (Yes/No/Maybe)")
    coworkers: str = Field(..., description="Willing to discuss with coworkers (Yes/No/Some of them)")
    supervisor: str = Field(..., description="Willing to discuss with supervisor (Yes/No/Some of them)")
    mental_health_interview: str = Field(..., description="Bring up in interview (Yes/No/Maybe)")
    phys_health_interview: str = Field(..., description="Bring up physical health in interview (Yes/No/Maybe)")
    mental_vs_physical: str = Field(..., description="Employer takes mental health seriously (Yes/No/Don't know)")
    obs_consequence: str = Field(..., description="Observed negative consequences (Yes/No)")

    @validator('Gender')
    def normalize_gender(cls, v):
        """Normalize gender input to handle variations"""
        v_lower = v.lower().strip()
        if v_lower in ['male', 'm', 'man', 'cis male', 'male-ish', 'maile', 'mal', 'male (cis)', 'make', 'male ', 'msle']:
            return 'Male'
        elif v_lower in ['female', 'f', 'woman', 'femake', 'female ', 'cis female', 'femail']:
            return 'Female'
        else:
            return 'Other'

    class Config:
        schema_extra = {
            "example": {
                "Age": 35,
                "Gender": "Male",
                "family_history": "Yes",
                "work_interfere": "Sometimes",
                "self_employed": "No",
                "no_employees": "26-100",
                "remote_work": "Yes",
                "tech_company": "Yes",
                "benefits": "Yes",
                "care_options": "Yes",
                "wellness_program": "Yes",
                "seek_help": "Yes",
                "anonymity": "Yes",
                "leave": "Somewhat easy",
                "mental_health_consequence": "Maybe",
                "phys_health_consequence": "No",
                "coworkers": "Some of them",
                "supervisor": "Yes",
                "mental_health_interview": "No",
                "phys_health_interview": "Maybe",
                "mental_vs_physical": "No",
                "obs_consequence": "Yes"
            }
        }


class PredictionResponse(BaseModel):
    """Response model for predictions"""
    prediction: str = Field(..., description="Treatment Needed or No Treatment Needed")
    confidence: float = Field(..., description="Confidence score (0-100)")
    details: Dict[str, Any] = Field(..., description="Additional prediction details")


@app.on_event("startup")
async def load_models():
    """Load ML models and encoders at startup"""
    global model, encoders
    
    try:
        logger.info("Loading model artifacts...")
        model = joblib.load('mental_health_osmi_model.pkl')
        encoders = joblib.load('osmi_encoders.pkl')
        logger.info("✅ Model and encoders loaded successfully")
        logger.info(f"Model type: {type(model).__name__}")
        logger.info(f"Number of encoders: {len(encoders)}")
        
        if hasattr(model, 'feature_names_in_'):
            logger.info(f"Expected features: {list(model.feature_names_in_)}")
        
    except FileNotFoundError as e:
        logger.error(f"❌ Model files not found: {e}")
        logger.error("Please ensure 'mental_health_osmi_model.pkl' and 'osmi_encoders.pkl' are in the working directory")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error loading models: {e}")
        sys.exit(1)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Mental Health Tracker API",
        "status": "running",
        "version": "1.0.0",
        "model_loaded": model is not None,
        "encoders_loaded": encoders is not None
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "encoders_loaded": encoders is not None,
        "encoder_count": len(encoders) if encoders else 0
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict_mental_health(user_response: UserResponse):
    """
    Predict mental health treatment needs based on user responses
    
    Args:
        user_response: UserResponse object containing all survey answers
        
    Returns:
        PredictionResponse with prediction, confidence, and details
    """
    try:
        # Step 1: Convert Pydantic model to DataFrame
        logger.info("Converting user response to DataFrame...")
        input_dict = user_response.dict()
        input_df = pd.DataFrame([input_dict])
        
        logger.info(f"Input columns: {list(input_df.columns)}")
        
        # Step 2: Gender is already normalized by the validator
        logger.info(f"Normalized Gender: {input_df['Gender'].iloc[0]}")
        
        # Step 3: Encode features using loaded encoders
        logger.info("Encoding categorical features...")
        for col, encoder in encoders.items():
            if col in input_df.columns:
                try:
                    original_value = input_df[col].iloc[0]
                    input_df[col] = encoder.transform([original_value])
                    logger.info(f"Encoded {col}: {original_value} -> {input_df[col].iloc[0]}")
                except ValueError as e:
                    # Handle unseen labels gracefully
                    logger.warning(f"⚠️ Unseen label in {col}: {input_df[col].iloc[0]}, defaulting to 0")
                    input_df[col] = 0
        
        # Step 4: CRITICAL - Reorder columns to match model.feature_names_in_
        if hasattr(model, 'feature_names_in_'):
            logger.info("Reordering columns to match model training order...")
            expected_features = list(model.feature_names_in_)
            logger.info(f"Expected feature order: {expected_features}")
            
            # Ensure all expected features are present
            missing_features = set(expected_features) - set(input_df.columns)
            if missing_features:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required features: {missing_features}"
                )
            
            # Reorder to match training
            input_df = input_df[expected_features]
            logger.info("✅ Columns reordered successfully")
        
        # Step 5: Make prediction
        logger.info("Making prediction...")
        prediction = model.predict(input_df)
        probability = model.predict_proba(input_df)
        
        # Step 6: Format response
        prediction_label = "Treatment Needed" if prediction[0] == 1 else "No Treatment Needed"
        confidence_score = float(probability[0][prediction[0]] * 100)
        
        logger.info(f"Prediction: {prediction_label}, Confidence: {confidence_score:.2f}%")
        
        response = PredictionResponse(
            prediction=prediction_label,
            confidence=round(confidence_score, 2),
            details={
                "prediction_class": int(prediction[0]),
                "probability_no_treatment": round(float(probability[0][0] * 100), 2),
                "probability_treatment_needed": round(float(probability[0][1] * 100), 2),
                "recommendation": (
                    "We recommend consulting a mental health professional based on your responses."
                    if prediction[0] == 1
                    else "Your responses suggest you are currently managing well. Continue monitoring your mental health."
                ),
                "age": user_response.Age,
                "gender": user_response.Gender
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during prediction: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )


@app.get("/model-info")
async def get_model_info():
    """Get information about the loaded model"""
    if model is None or encoders is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    info = {
        "model_type": type(model).__name__,
        "encoder_count": len(encoders),
        "encoded_features": list(encoders.keys())
    }
    
    if hasattr(model, 'feature_names_in_'):
        info["feature_names"] = list(model.feature_names_in_)
        info["feature_count"] = len(model.feature_names_in_)
    
    if hasattr(model, 'n_estimators'):
        info["n_estimators"] = model.n_estimators
    
    return info


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
