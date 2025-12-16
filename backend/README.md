# Mental Health Tracker API - Backend

This directory contains the backend API for the Mental Health Tracker application. All the API source code, including the model and server configuration, resides inside the `backend/` folder. It is built using **FastAPI** and uses a pre-trained **Random Forest Classifier** to predict whether a user needs mental health treatment based on their survey responses.

## 🚀 Project Setup

Follow these steps to set up and run the backend server locally.

### Prerequisites

- Python 3.9 or higher
- `pip` (Python package manager)

### 1. Create a Virtual Environment (Optional but Recommended)

It is best practice to run Python projects in a virtual environment to manage dependencies locally.

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

Install the required Python packages listed in `requirements.txt`.

```bash
pip install -r requirements.txt
```

### 3. Run the Server

You can run the server directly using Python or via Uvicorn.

```bash
# Option 1: Using Python
python main.py

# Option 2: Using Uvicorn (with hot reload for development)
uvicorn main:app --reload
```

The server will start at `http://localhost:8000`.

- **API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative Documentation (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📂 Key Files & Dataset

Here is a breakdown of the important files in this project:

- **`backend/mental_health_osmi_model.pkl`**:
  This is the trained **Random Forest Classifier** model saved as a serialized file. The API loads this file to make real-time predictions.

- **`backend/osmi_encoders.pkl`**:
  This file contains the **LabelEncoders** created during the training phase. It ensures that the user's input (string values like "Yes", "No", "Male") is converted into the exact same numerical format that the model was trained on.

- **`survey.csv`** (in project root):
  The raw dataset used to train the model. This is the **Open Sourcing Mental Illness (OSMI) Mental Health in Tech Survey 2014**. It contains the historical data from which the model learned the patterns connecting workplace factors to mental health needs.

- **`backend/main.py`**:
  The main source code for the FastAPI server. It handles the API endpoints, data validation, and connects the user's input to the model.

---

## 🌲 Random Forest Classifier Model Explained

The core of this application is a **Random Forest Classifier**. Below is a detailed explanation of what this model is, how it works, and why it is effective for this specific problem.

### What is a Random Forest?

Random Forest is a popular **supervised machine learning algorithm** used for both classification and regression problems. It is an **ensemble learning** method, which means it combines multiple individual models to produce a single, stronger prediction.

As the name suggests, it creates a "forest" of **Decision Trees**.

### How It Works

1.  **Decision Trees (The Building Blocks)**:
    -   Imagine a flowchart where each question (e.g., "Do you work remotely?") splits the data into branches.
    -   We keep asking questions until we reach a final decision (leaf node).
    -   A single decision tree can be prone to *overfitting*—it might memorize the training data too well and fail on new data.

2.  **The "Random" in Random Forest**:
    -   **Bootstrapping (Bagging)**: Instead of training one tree on all the data, Random Forest creates many trees (e.g., 100 trees). Each tree is trained on a random subset of the data (sampled with replacement).
    -   **Feature Randomness**: When splitting a node, instead of looking at *all* features to find the best split, the algorithm selects a random subset of features. This ensures that the trees are diverse and not correlated (i.e., they don't all make the same mistakes).

3.  **Majority Voting (Aggregation)**:
    -   When we want to make a prediction for a new user, we pass their data through *every* tree in the forest.
    -   Each tree gives a "vote" (e.g., Tree 1 says "Treatment Needed", Tree 2 says "No Treatment").
    -   The final output is determined by the **majority vote**. If 70 out of 100 trees say "Treatment Needed", the model predicts "Treatment Needed".

### Why Random Forest for Mental Health Prediction?

*   **Robustness**: By averaging many trees, it cancels out the errors and biases of individual trees, making it very stable.
*   **Handles Categorical Data**: The mental health survey has many categorical fields (e.g., Gender, Yes/No questions), which Random Forest handles effectively (after encoding).
*   **Feature Importance**: It can implicitly identify which questions (features) are most critical for predicting mental health needs (e.g., "Family History" might be a more important splitter than "Remote Work").
*   **Non-Linear Relationships**: It can capture complex, non-linear patterns in the data that a simple linear model might miss.

### Model Specifics in This Project

-   **Algorithm**: `sklearn.ensemble.RandomForestClassifier`
-   **Training Data**: OSMI Mental Health in Tech Survey 2014.
-   **Features Used**:
    -   **Personal**: Age, Gender
    -   **Work Environment**: Remote work, Tech company, Company size, Benefits, Wellness program, etc.
    -   **Mental Health Context**: Family history, Work interference, Willingness to seek help.
-   **Prediction Output**:
    -   **0 (No)**: Likely does not need immediate professional treatment.
    -   **1 (Yes)**: Likely benefits from professional mental health treatment.
