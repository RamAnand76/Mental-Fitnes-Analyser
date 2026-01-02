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
- **AI-Powered Insights**: Generate weekly/monthly wellness reports from journal entries using Google Gemini.
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

Predict mental health treatment needs based on a survey response.

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
