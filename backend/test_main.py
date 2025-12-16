"""
Test Suite for Mental Health Tracker API
Tests model loading, prediction endpoint, and edge cases
"""

import pytest
from fastapi.testclient import TestClient
from main import app, model, encoders
import sys

# Create test client
client = TestClient(app)


class TestAPIStartup:
    """Test application startup and model loading"""
    
    def test_models_loaded(self):
        """Test 1: Verify the application starts and models are loaded"""
        # Trigger startup event by making a request
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_loaded"] is True
        assert data["encoders_loaded"] is True
        assert data["encoder_count"] > 0
        
        print("✅ Test 1 Passed: Models loaded successfully")
    
    def test_root_endpoint(self):
        """Test root endpoint returns correct information"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "running"
        assert data["model_loaded"] is True
        assert data["version"] == "1.0.0"
        
        print("✅ Root endpoint test passed")
    
    def test_model_info_endpoint(self):
        """Test model info endpoint"""
        response = client.get("/model-info")
        assert response.status_code == 200
        
        data = response.json()
        assert "model_type" in data
        assert "encoder_count" in data
        assert "encoded_features" in data
        assert isinstance(data["encoded_features"], list)
        
        print("✅ Model info endpoint test passed")


class TestPredictionEndpoint:
    """Test the /predict endpoint with various inputs"""
    
    def test_valid_prediction_treatment_needed(self):
        """Test 2: Send a valid POST request and verify response structure"""
        # Sample input that might indicate treatment needed
        payload = {
            "Age": 35,
            "Gender": "Male",
            "family_history": "Yes",
            "work_interfere": "Often",
            "self_employed": "No",
            "no_employees": "26-100",
            "remote_work": "Yes",
            "tech_company": "Yes",
            "benefits": "No",
            "care_options": "No",
            "wellness_program": "No",
            "seek_help": "No",
            "anonymity": "No",
            "leave": "Very difficult",
            "mental_health_consequence": "Yes",
            "phys_health_consequence": "No",
            "coworkers": "No",
            "supervisor": "No",
            "mental_health_interview": "No",
            "phys_health_interview": "Maybe",
            "mental_vs_physical": "No",
            "obs_consequence": "Yes"
        }
        
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify response structure
        assert "prediction" in data
        assert "confidence" in data
        assert "details" in data
        
        # Verify prediction is binary
        assert data["prediction"] in ["Treatment Needed", "No Treatment Needed"]
        
        # Verify confidence is a valid percentage
        assert 0 <= data["confidence"] <= 100
        assert isinstance(data["confidence"], (int, float))
        
        # Verify details structure
        assert "prediction_class" in data["details"]
        assert data["details"]["prediction_class"] in [0, 1]
        assert "probability_no_treatment" in data["details"]
        assert "probability_treatment_needed" in data["details"]
        assert "recommendation" in data["details"]
        assert "age" in data["details"]
        assert "gender" in data["details"]
        
        print(f"✅ Test 2 Passed: Valid prediction received")
        print(f"   Prediction: {data['prediction']}")
        print(f"   Confidence: {data['confidence']}%")
    
    def test_valid_prediction_no_treatment(self):
        """Test with input that might indicate no treatment needed"""
        payload = {
            "Age": 28,
            "Gender": "Female",
            "family_history": "No",
            "work_interfere": "Never",
            "self_employed": "No",
            "no_employees": "26-100",
            "remote_work": "No",
            "tech_company": "Yes",
            "benefits": "Yes",
            "care_options": "Yes",
            "wellness_program": "Yes",
            "seek_help": "Yes",
            "anonymity": "Yes",
            "leave": "Very easy",
            "mental_health_consequence": "No",
            "phys_health_consequence": "No",
            "coworkers": "Yes",
            "supervisor": "Yes",
            "mental_health_interview": "Maybe",
            "phys_health_interview": "Yes",
            "mental_vs_physical": "Yes",
            "obs_consequence": "No"
        }
        
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["prediction"] in ["Treatment Needed", "No Treatment Needed"]
        assert 0 <= data["confidence"] <= 100
        
        print(f"✅ Valid prediction test 2 passed")
        print(f"   Prediction: {data['prediction']}")


class TestEdgeCases:
    """Test edge cases and input normalization"""
    
    def test_messy_gender_input_male_ish(self):
        """Test 3: Test edge case with messy Gender input like 'Male-ish'"""
        payload = {
            "Age": 30,
            "Gender": "Male-ish",  # Edge case: non-standard gender input
            "family_history": "Yes",
            "work_interfere": "Sometimes",
            "self_employed": "No",
            "no_employees": "6-25",
            "remote_work": "Yes",
            "tech_company": "Yes",
            "benefits": "Yes",
            "care_options": "Not sure",
            "wellness_program": "Don't know",
            "seek_help": "Yes",
            "anonymity": "Yes",
            "leave": "Somewhat easy",
            "mental_health_consequence": "Maybe",
            "phys_health_consequence": "No",
            "coworkers": "Some of them",
            "supervisor": "Yes",
            "mental_health_interview": "No",
            "phys_health_interview": "Maybe",
            "mental_vs_physical": "Don't know",
            "obs_consequence": "No"
        }
        
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify normalization worked
        assert data["details"]["gender"] == "Male"  # Should be normalized to "Male"
        assert data["prediction"] in ["Treatment Needed", "No Treatment Needed"]
        assert 0 <= data["confidence"] <= 100
        
        print(f"✅ Test 3 Passed: Gender normalization works correctly")
        print(f"   Input: 'Male-ish' -> Normalized to: '{data['details']['gender']}'")
        print(f"   Prediction: {data['prediction']}")
    
    def test_various_gender_inputs(self):
        """Test various gender input variations"""
        gender_variations = [
            ("cis male", "Male"),
            ("woman", "Female"),
            ("M", "Male"),
            ("F", "Female"),
            ("man", "Male"),
            ("MALE", "Male"),
            ("female ", "Female"),
            ("non-binary", "Other"),
            ("agender", "Other")
        ]
        
        base_payload = {
            "Age": 25,
            "family_history": "No",
            "work_interfere": "Never",
            "self_employed": "No",
            "no_employees": "26-100",
            "remote_work": "No",
            "tech_company": "Yes",
            "benefits": "Yes",
            "care_options": "Yes",
            "wellness_program": "Yes",
            "seek_help": "Yes",
            "anonymity": "Yes",
            "leave": "Very easy",
            "mental_health_consequence": "No",
            "phys_health_consequence": "No",
            "coworkers": "Yes",
            "supervisor": "Yes",
            "mental_health_interview": "Maybe",
            "phys_health_interview": "Yes",
            "mental_vs_physical": "Yes",
            "obs_consequence": "No"
        }
        
        for input_gender, expected_normalized in gender_variations:
            payload = {**base_payload, "Gender": input_gender}
            response = client.post("/predict", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["details"]["gender"] == expected_normalized
            
            print(f"   ✓ '{input_gender}' -> '{expected_normalized}'")
        
        print("✅ All gender variations normalized correctly")
    
    def test_age_boundaries(self):
        """Test age boundary validation"""
        base_payload = {
            "Gender": "Male",
            "family_history": "No",
            "work_interfere": "Never",
            "self_employed": "No",
            "no_employees": "26-100",
            "remote_work": "No",
            "tech_company": "Yes",
            "benefits": "Yes",
            "care_options": "Yes",
            "wellness_program": "Yes",
            "seek_help": "Yes",
            "anonymity": "Yes",
            "leave": "Very easy",
            "mental_health_consequence": "No",
            "phys_health_consequence": "No",
            "coworkers": "Yes",
            "supervisor": "Yes",
            "mental_health_interview": "Maybe",
            "phys_health_interview": "Yes",
            "mental_vs_physical": "Yes",
            "obs_consequence": "No"
        }
        
        # Test valid ages
        for age in [18, 25, 50, 100]:
            payload = {**base_payload, "Age": age}
            response = client.post("/predict", json=payload)
            assert response.status_code == 200
        
        # Test invalid ages (should fail validation)
        for age in [17, 101]:
            payload = {**base_payload, "Age": age}
            response = client.post("/predict", json=payload)
            assert response.status_code == 422  # Validation error
        
        print("✅ Age boundary validation working correctly")
    
    def test_missing_fields(self):
        """Test that missing required fields return validation error"""
        incomplete_payload = {
            "Age": 30,
            "Gender": "Male",
            # Missing other required fields
        }
        
        response = client.post("/predict", json=incomplete_payload)
        assert response.status_code == 422  # Validation error
        
        print("✅ Missing fields validation working correctly")


class TestProbabilityConsistency:
    """Test that probabilities are consistent"""
    
    def test_probabilities_sum_to_100(self):
        """Verify that probability percentages sum to approximately 100"""
        payload = {
            "Age": 32,
            "Gender": "Female",
            "family_history": "Yes",
            "work_interfere": "Sometimes",
            "self_employed": "No",
            "no_employees": "100-500",
            "remote_work": "Yes",
            "tech_company": "Yes",
            "benefits": "Yes",
            "care_options": "Yes",
            "wellness_program": "No",
            "seek_help": "Yes",
            "anonymity": "Don't know",
            "leave": "Somewhat easy",
            "mental_health_consequence": "Maybe",
            "phys_health_consequence": "No",
            "coworkers": "Some of them",
            "supervisor": "Some of them",
            "mental_health_interview": "No",
            "phys_health_interview": "Maybe",
            "mental_vs_physical": "No",
            "obs_consequence": "No"
        }
        
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        prob_no_treatment = data["details"]["probability_no_treatment"]
        prob_treatment = data["details"]["probability_treatment_needed"]
        
        # Sum should be approximately 100 (allowing for rounding)
        total = prob_no_treatment + prob_treatment
        assert 99.9 <= total <= 100.1
        
        print(f"✅ Probabilities sum correctly: {prob_no_treatment}% + {prob_treatment}% = {total}%")


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
