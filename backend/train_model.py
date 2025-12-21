import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
import joblib
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def train():
    try:
        # Load dataset
        logger.info("Loading dataset...")
        csv_path = os.path.join(os.path.dirname(__file__), '../survey.csv')
        df = pd.read_csv(csv_path)
        
        # Features to keep (matching our API schema)
        features = [
            'Age', 'Gender', 'family_history', 'work_interfere', 'self_employed',
            'no_employees', 'remote_work', 'tech_company', 'benefits', 'care_options',
            'wellness_program', 'seek_help', 'anonymity', 'leave',
            'mental_health_consequence', 'phys_health_consequence', 'coworkers',
            'supervisor', 'mental_health_interview', 'phys_health_interview',
            'mental_vs_physical', 'obs_consequence'
        ]
        target = 'treatment'
        
        # Filter columns
        df = df[features + [target]]
        
        # 1. Handle Age
        # Filter out outliers (18-100)
        df = df[(df['Age'] >= 18) & (df['Age'] <= 100)]
        
        # 2. Handle Gender Normalization
        def clean_gender(gender):
            if isinstance(gender, str):
                g = gender.lower().strip()
                if g in ['male', 'm', 'man', 'cis male', 'male-ish', 'maile', 'mal', 'male (cis)', 'make', 'male ', 'msle']:
                    return 'Male'
                elif g in ['female', 'f', 'woman', 'femake', 'female ', 'cis female', 'femail']:
                    return 'Female'
                else:
                    return 'Other'
            return 'Other'
            
        df['Gender'] = df['Gender'].apply(clean_gender)
        
        # 3. Handle Missing Values
        # work_interfere often has NaNs
        df['work_interfere'] = df['work_interfere'].fillna('Don\'t know')
        df['self_employed'] = df['self_employed'].fillna('No')
        
        # Drop remaining NaNs for simplicity or impute
        df.dropna(inplace=True)
        
        # 4. Encoding
        logger.info("Encoding features...")
        encoders = {}
        for col in df.columns:
            if df[col].dtype == 'object':
                le = LabelEncoder()
                df[col] = le.fit_transform(df[col])
                # Save encoders for features only
                if col != target:
                    encoders[col] = le
        
        # 5. Split Data
        X = df.drop(target, axis=1)
        y = df[target]
        
        # 6. Train Model
        logger.info("Training Random Forest Model...")
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(X, y)
        
        # 7. Save Artifacts
        logger.info("Saving model and encoders...")
        joblib.dump(rf, 'mental_health_osmi_model.pkl')
        joblib.dump(encoders, 'osmi_encoders.pkl')
        
        logger.info("✅ Model training completed successfully!")
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise

if __name__ == "__main__":
    train()
