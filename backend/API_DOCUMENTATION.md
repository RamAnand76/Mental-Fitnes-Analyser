# Mental Health Tracker API Documentation

**Version:** 2.0.0  
**Base URL:** `http://localhost:8000`  
**Interactive Docs:** [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
   - [Root](#root)
   - [Authentication Endpoints](#authentication-endpoints)
   - [Journal Endpoints](#journal-endpoints)
   - [Prediction Endpoints](#prediction-endpoints)
4. [Data Models (Schemas)](#data-models-schemas)
5. [Error Handling](#error-handling)

---

## Overview

The Mental Health Tracker API provides a RESTful interface for:

- **User Authentication**: Signup, login, token refresh, and logout.
- **Journal Management**: Create, read, update, and delete personal journal entries with automatic sentiment analysis.
- **Voice Journaling**: Audio recording upload and AI processing for Pitch, Speed, Transcription, and dominant emotional labels. This audio is stored entirely as Base64.
- **Wearable Integration**: Google OAuth 2.0 authorization and integration with Google Fit to store daily Steps and Resting Heart Rates.
- **AI-Powered Insights**: Generate weekly/monthly wellness reports from journal entries using Google Gemini.
- **Correlation Engine**: Algorithm to match physical tracking data against acoustic voice metrics.
- **Mental Health Prediction**: Predict the likelihood of needing mental health treatment based on a survey using a Random Forest classifier.

All protected endpoints require a **Bearer JWT token** in the `Authorization` header.

---

## Authentication

This API uses **JWT (JSON Web Tokens)** for authentication.

### How to Authenticate

1. **Sign up** or **Log in** to receive an `access_token` and a `refresh_token`.
2. Include the `access_token` in the `Authorization` header for all protected requests:

   ```
   Authorization: Bearer <your_access_token>
   ```

3. When the `access_token` expires, use the `/auth/refresh` endpoint with your `refresh_token` to get a new token pair.

---

## API Endpoints

### Root

#### `GET /`

Health check endpoint for the API.

**Response:**

```json
{
  "message": "Welcome to Mental Health Tracker API v2"
}
```

---

### Authentication Endpoints

All authentication endpoints are prefixed with `/auth`.

---

#### `POST /auth/signup`

Register a new user account.

**Request Body:**

| Field      | Type   | Required | Description                |
| ---------- | ------ | -------- | -------------------------- |
| `email`    | string | Yes      | A valid email address.     |
| `password` | string | Yes      | The user's password.       |

**Example Request:**

```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Success Response (200 OK):**

```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2026-01-02T10:30:00.000000"
}
```

**Error Responses:**

| Status Code | Detail                      |
| ----------- | --------------------------- |
| 400         | `Email already registered`  |
| 422         | Validation error (e.g., invalid email format) |

---

#### `POST /auth/login`

Authenticate a user and receive access/refresh tokens.

**Request Body (Form Data - `application/x-www-form-urlencoded`):**

| Field      | Type   | Required | Description                        |
| ---------- | ------ | -------- | ---------------------------------- |
| `username` | string | Yes      | The user's email address.          |
| `password` | string | Yes      | The user's password.               |

> **Note:** This endpoint uses OAuth2 password flow, so the email is sent as `username`.

**Example Request (cURL):**

```bash
curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=user@example.com&password=securepassword123"
```

**Success Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses:**

| Status Code | Detail              |
| ----------- | ------------------- |
| 404         | `Invalid credentials` |

---

#### `POST /auth/refresh`

Get a new access token using a refresh token.

**Query Parameters:**

| Parameter | Type   | Required | Description               |
| --------- | ------ | -------- | ------------------------- |
| `token`   | string | Yes      | The user's refresh token. |

**Example Request (cURL):**

```bash
curl -X POST "http://localhost:8000/auth/refresh?token=<your_refresh_token>"
```

**Success Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses:**

| Status Code | Detail                          |
| ----------- | ------------------------------- |
| 401         | `Could not validate credentials` |

---

#### `POST /auth/signout`

Sign out the user. Since JWTs are stateless, the client should discard the token.

**Success Response (200 OK):**

```json
{
  "message": "Successfully signed out"
}
```

---

### Journal Endpoints

All journal endpoints are prefixed with `/journals` and **require authentication**.

---

#### `GET /journals/`

Retrieve all journal entries for the authenticated user.

**Headers:**

```
Authorization: Bearer <access_token>
```

**Success Response (200 OK):**

```json
[
  {
    "id": 1,
    "content": "Today was a productive day.",
    "user_id": 1,
    "mood_score": 0.85,
    "sentiment_label": "Positive",
    "created_at": "2026-01-02T09:00:00.000000"
  },
  {
    "id": 2,
    "content": "Feeling a bit stressed about deadlines.",
    "user_id": 1,
    "mood_score": -0.45,
    "sentiment_label": "Negative",
    "created_at": "2026-01-01T22:30:00.000000"
  }
]
```

---

#### `POST /journals/`

Create a new journal entry. Sentiment is analyzed automatically.

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request Body:**

| Field        | Type   | Required | Description                                      |
| ------------ | ------ | -------- | ------------------------------------------------ |
| `content`    | string | Yes      | The text content of the journal entry.           |
| `entry_date` | string | No       | Custom date for the entry (format: `YYYY-MM-DD`).|
| `entry_time` | string | No       | Custom time for the entry (format: `HH:MM`).     |

**Example Request:**

```json
{
  "content": "Had a great morning workout!",
  "entry_date": "2026-01-02",
  "entry_time": "07:30"
}
```

**Success Response (200 OK):**

```json
{
  "id": 3,
  "content": "Had a great morning workout!",
  "user_id": 1,
  "mood_score": 0.92,
  "sentiment_label": "Positive",
  "created_at": "2026-01-02T07:30:00.000000"
}
```

---

#### `GET /journals/{journal_id}`

Retrieve a specific journal entry by its ID.

**Path Parameters:**

| Parameter    | Type | Description                     |
| ------------ | ---- | ------------------------------- |
| `journal_id` | int  | The unique ID of the journal.   |

**Success Response (200 OK):**

```json
{
  "id": 1,
  "content": "Today was a productive day.",
  "user_id": 1,
  "mood_score": 0.85,
  "sentiment_label": "Positive",
  "created_at": "2026-01-02T09:00:00.000000"
}
```

**Error Responses:**

| Status Code | Detail              |
| ----------- | ------------------- |
| 404         | `Journal not found` |

---

#### `PUT /journals/{journal_id}`

Update an existing journal entry. Sentiment is re-analyzed.

**Path Parameters:**

| Parameter    | Type | Description                     |
| ------------ | ---- | ------------------------------- |
| `journal_id` | int  | The unique ID of the journal.   |

**Request Body:**

| Field     | Type   | Required | Description                            |
| --------- | ------ | -------- | -------------------------------------- |
| `content` | string | Yes      | The updated content of the journal.    |

**Success Response (200 OK):**

```json
{
  "id": 1,
  "content": "Updated: Today was incredibly productive!",
  "user_id": 1,
  "mood_score": 0.95,
  "sentiment_label": "Positive",
  "created_at": "2026-01-02T09:00:00.000000"
}
```

---

#### `DELETE /journals/{journal_id}`

Delete a journal entry.

**Path Parameters:**

| Parameter    | Type | Description                     |
| ------------ | ---- | ------------------------------- |
| `journal_id` | int  | The unique ID of the journal.   |

**Success Response (200 OK):**

```json
{
  "message": "Journal deleted successfully"
}
```

---

#### `GET /journals/insights/report`

Generate a wellness report for a custom period.

**Query Parameters:**

| Parameter | Type   | Default | Description                           |
| --------- | ------ | ------- | ------------------------------------- |
| `period`  | string | `7d`    | Period for analysis: `7d` or `30d`.   |

**Success Response (200 OK):**

```json
{
  "report": "Based on your entries, you've shown consistent positive moods...",
  "period": "Last 7 days",
  "entries_analyzed": 5
}
```

---

#### `GET /journals/insights/weekly`

Generate a weekly wellness report (last 7 days).

**Success Response (200 OK):**

```json
{
  "report": "Your week shows overall positive engagement...",
  "period": "Last 7 days",
  "entries_analyzed": 7
}
```

---

#### `GET /journals/insights/monthly`

Generate a monthly wellness report (last 30 days).

**Success Response (200 OK):**

```json
{
  "report": "Over the past month, your journal entries indicate...",
  "period": "Last 30 days",
  "entries_analyzed": 28
}
```

---

### Prediction Endpoints

---

#### `POST /predict`

Predict mental health treatment needs based on a survey response. This endpoint uses a Random Forest classifier trained on the OSMI 2014 Mental Health in Tech Survey dataset.

---

##### Survey Questionnaire

The following questions are presented to the user. Each question has specific valid options:

| # | Question | Field Name | Valid Options |
|---|----------|------------|---------------|
| 1 | What is your age? | `Age` | Any integer (e.g., 25, 35, 45) |
| 2 | What is your gender? | `Gender` | `Male`, `Female`, `Other` |
| 3 | Do you have a family history of mental illness? | `family_history` | `Yes`, `No` |
| 4 | If you have a mental health condition, does it interfere with your work? | `work_interfere` | `Often`, `Rarely`, `Never`, `Sometimes`, `Unknown` |
| 5 | Are you self-employed? | `self_employed` | `Yes`, `No` |
| 6 | How many employees does your company have? | `no_employees` | `1-5`, `6-25`, `26-100`, `100-500`, `500-1000`, `More than 1000` |
| 7 | Do you work remotely at least 50% of the time? | `remote_work` | `Yes`, `No` |
| 8 | Is your employer primarily a tech company/organization? | `tech_company` | `Yes`, `No` |
| 9 | Does your employer provide mental health benefits? | `benefits` | `Yes`, `No`, `Don't know` |
| 10 | Do you know the options for mental health care your employer provides? | `care_options` | `Yes`, `No`, `Not sure` |
| 11 | Has your employer ever discussed mental health as part of a wellness program? | `wellness_program` | `Yes`, `No`, `Don't know` |
| 12 | Does your employer provide resources to learn more about mental health issues and how to seek help? | `seek_help` | `Yes`, `No`, `Don't know` |
| 13 | Is your anonymity protected if you choose to take advantage of mental health resources? | `anonymity` | `Yes`, `No`, `Don't know` |
| 14 | How easy is it for you to take medical leave for a mental health condition? | `leave` | `Very easy`, `Somewhat easy`, `Somewhat difficult`, `Very difficult`, `Don't know` |
| 15 | Do you think that discussing a mental health issue with your employer would have negative consequences? | `mental_health_consequence` | `Yes`, `No`, `Maybe` |
| 16 | Do you think that discussing a physical health issue with your employer would have negative consequences? | `phys_health_consequence` | `Yes`, `No`, `Maybe` |
| 17 | Would you be willing to discuss a mental health issue with your coworkers? | `coworkers` | `Yes`, `No`, `Some of them` |
| 18 | Would you be willing to discuss a mental health issue with your direct supervisor? | `supervisor` | `Yes`, `No`, `Some of them` |
| 19 | Would you bring up a mental health issue with a potential employer in an interview? | `mental_health_interview` | `Yes`, `No`, `Maybe` |
| 20 | Would you bring up a physical health issue with a potential employer in an interview? | `phys_health_interview` | `Yes`, `No`, `Maybe` |
| 21 | Do you feel that your employer takes mental health as seriously as physical health? | `mental_vs_physical` | `Yes`, `No`, `Don't know` |
| 22 | Have you heard of or observed negative consequences for coworkers with mental health conditions in your workplace? | `obs_consequence` | `Yes`, `No` |

---

**Request Body (SurveyResponse):**

| Field                       | Type   | Description                                                             |
| --------------------------- | ------ | ----------------------------------------------------------------------- |
| `Age`                       | int    | User's age (e.g., 35).                                                  |
| `Gender`                    | string | Gender: `Male`, `Female`, or `Other`.                                   |
| `family_history`            | string | Family history of mental illness: `Yes` / `No`.                         |
| `work_interfere`            | string | Work interference: `Often`, `Rarely`, `Never`, `Sometimes`, `Unknown`.  |
| `self_employed`             | string | Self-employed: `Yes` / `No`.                                            |
| `no_employees`              | string | Company size: `1-5`, `6-25`, `26-100`, `100-500`, `500-1000`, `More than 1000`. |
| `remote_work`               | string | Remote work: `Yes` / `No`.                                              |
| `tech_company`              | string | Works at tech company: `Yes` / `No`.                                    |
| `benefits`                  | string | Mental health benefits: `Yes`, `No`, `Don't know`.                      |
| `care_options`              | string | Knows care options: `Yes`, `No`, `Not sure`.                            |
| `wellness_program`          | string | Wellness program discussed: `Yes`, `No`, `Don't know`.                  |
| `seek_help`                 | string | Resources to seek help: `Yes`, `No`, `Don't know`.                      |
| `anonymity`                 | string | Anonymity protected: `Yes`, `No`, `Don't know`.                         |
| `leave`                     | string | Ease of leave: `Very easy`, `Somewhat easy`, `Somewhat difficult`, `Very difficult`, `Don't know`. |
| `mental_health_consequence` | string | Consequences of discussing mental health: `Yes`, `No`, `Maybe`.         |
| `phys_health_consequence`   | string | Consequences of discussing physical health: `Yes`, `No`, `Maybe`.       |
| `coworkers`                 | string | Discuss with coworkers: `Yes`, `No`, `Some of them`.                    |
| `supervisor`                | string | Discuss with supervisor: `Yes`, `No`, `Some of them`.                   |
| `mental_health_interview`   | string | Bring up in interview: `Yes`, `No`, `Maybe`.                            |
| `phys_health_interview`     | string | Bring up physical health in interview: `Yes`, `No`, `Maybe`.            |
| `mental_vs_physical`        | string | Employer takes mental health seriously: `Yes`, `No`, `Don't know`.      |
| `obs_consequence`           | string | Observed negative consequences: `Yes` / `No`.                           |

**Example Request:**

```json
{
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
```

**Success Response (200 OK):**

```json
{
  "prediction": "Treatment Needed",
  "confidence": 78.5,
  "details": {
    "prediction_class": 1,
    "recommendation": "Consult professional"
  }
}
```

**Error Responses:**

| Status Code | Detail             |
| ----------- | ------------------ |
| 503         | `Model not loaded` |
| 500         | Internal error     |

---

### Voice Endpoints

---

#### `POST /voice/upload`

Upload a voice recording. The system will extract acoustic features (pitch, speed) via `librosa`, and output a dominant emotion prediction string via Hugging Face. Furthermore, it will run `openai-whisper` to transcribe the audio into text, and save the audio itself into the SQLite database as an encoded Base64 string.

**Query Parameters:**
| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| `user_id` | int  | Yes      | Internal ID of user uploading the file. |

**Form Data (Multipart Upload):**

| Field        | Type   | Required | Description |
| ------------ | ------ | -------- | ----------- |
| `audio_file` | File   | Yes      | File body (.wav, .mp3, .m4a, .ogg) |

**Success Response (200 OK):**
```json
{
  "message": "Voice journal analyzed successfully",
  "insights": {
    "journal_id": 12,
    "emotion": "happy",
    "confidence": 0.89,
    "acoustics": {
      "average_pitch_hz": 125.4,
      "speaking_speed_bpm": 120.3
    }
  }
}
```

---

#### `GET /voice/journals`

Retrieve a list of all historical voice recordings and insights for a specific user.

**Query Parameters:**
| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| `user_id` | int  | Yes      | Your local system User ID. |

**Success Response (200 OK):**
```json
[
  {
    "transcription": "I'm having a really great day today.",
    "pitch_mean": 154.2,
    "speed_rate": 115.0,
    "dominant_emotion": "happy",
    "id": 1,
    "user_id": 1,
    "audio_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA...",
    "created_at": "2026-02-22T12:00:00"
  }
]
```

---

### Wearable Endpoints

---

#### `GET /wearables/auth/google/login`

Initiate the Google OAuth 2.0 process for authorizing Google Fit parameters.

**Query Parameters:**
| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| `user_id` | int  | Yes      | Your local system User ID. |

**Success Response (200 OK):** Provides an `authorization_url` to direct the frontend window.

#### `POST /wearables/sync`

Pulls user's Step Count and Resting Heart Rate averages for the last 30 days (1-day buckets) from Google Fit and persists them in the database, avoiding duplicates. Also returns today's current data separately in the `data` obj.

**Query Parameters:**
| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| `user_id` | int  | Yes      | Your local system User ID. |

**Success Response (200 OK):**
```json
{
  "message": "Successfully synchronized Google Fit data",
  "data": {
    "steps": 10543,
    "heart_rate": 65.5,
    "date": "2026-02-22T13:45:00.000"
  },
  "history": [
    {
      "steps": 10543,
      "heart_rate": 65.5,
      "date": "2026-02-22T13:00:00"
    },
    {
      "steps": 8000,
      "heart_rate": 68.0,
      "date": "2026-02-21T13:00:00"
    }
  ]
}
```

---

### Insights Endpoints

---

#### `GET /insights/correlations`

Calculates localized Pearson correlations joining user Wearable logs (Steps, HR) against their Voice Acoustic data (Pitch, Speed). It requires a minimum of 3 overlapping day logs from both sets.

**Query Parameters:**
| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| `user_id` | int  | Yes      | Your local system User ID. |

**Success Response (200 OK):** Returns raw correlation matrices and natural language string outputs.

## Data Models (Schemas)

### User

| Field        | Type     | Description                |
| ------------ | -------- | -------------------------- |
| `id`         | int      | Unique user ID.            |
| `email`      | string   | User's email address.      |
| `created_at` | datetime | Account creation timestamp.|

### Token

| Field           | Type   | Description          |
| --------------- | ------ | -------------------- |
| `access_token`  | string | JWT access token.    |
| `refresh_token` | string | JWT refresh token.   |
| `token_type`    | string | Always `bearer`.     |

### Journal

| Field             | Type     | Description                               |
| ----------------- | -------- | ----------------------------------------- |
| `id`              | int      | Unique journal ID.                        |
| `content`         | string   | Journal entry text.                       |
| `user_id`         | int      | Owner user ID.                            |
| `mood_score`      | float    | Sentiment score (-1 to 1).                |
| `sentiment_label` | string   | `Positive`, `Negative`, or `Neutral`.     |
| `created_at`      | datetime | Entry creation timestamp.                 |

### VoiceJournal

| Field              | Type     | Description                                |
| ------------------ | -------- | ------------------------------------------ |
| `id`               | int      | Internal Database ID.                      |
| `audio_base64`     | string   | Raw base64 string of the Audio Data.       |
| `transcription`    | string   | Text transcription via Whisper AI.         |
| `pitch_mean`       | float    | F0 Hz Base Frequency via Librosa.          |
| `speed_rate`       | float    | Speech Speed/BPM.                          |
| `dominant_emotion` | string   | Result category of the HF transformer.     |

### WearableData

| Field                | Type     | Description                           |
| -------------------- | -------- | ------------------------------------- |
| `date`               | datetime | Timelog for values.                   |
| `step_count`         | int      | Daily aggregated steps.               |
| `resting_heart_rate` | float    | Overall average derived heart rate.   |

### PredictionResponse

| Field        | Type   | Description                                    |
| ------------ | ------ | ---------------------------------------------- |
| `prediction` | string | `Treatment Needed` or `No Treatment Needed`.   |
| `confidence` | float  | Confidence percentage (0-100).                 |
| `details`    | object | Contains `prediction_class` and `recommendation`. |

---

## Error Handling

All errors follow a consistent format:

```json
{
  "detail": "Error message describing the issue."
}
```

### Common HTTP Status Codes

| Status Code | Description                                      |
| ----------- | ------------------------------------------------ |
| 200         | Success.                                         |
| 400         | Bad Request (e.g., email already registered).    |
| 401         | Unauthorized (invalid or missing token).         |
| 404         | Not Found (resource doesn't exist).              |
| 422         | Validation Error (invalid input format).         |
| 500         | Internal Server Error.                           |
| 503         | Service Unavailable (e.g., model not loaded).    |

---

## Contact

For issues or feature requests, please contact the development team.
