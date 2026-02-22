from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, journal, predict, google_fit, voice, correlation
from app.database import engine, Base
from app.routers.predict import load_prediction_models

# Create Tables
# In production, use Alembic. For this project, auto-create is fine.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Mental Health Tracker API",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load ML Models on Startup
@app.on_event("startup")
async def startup_event():
    load_prediction_models()

# Include Routers
app.include_router(auth.router)
app.include_router(journal.router)
app.include_router(predict.router)
app.include_router(google_fit.router)
app.include_router(voice.router)
app.include_router(correlation.router)

@app.get("/")
def root():
    return {"message": "Welcome to Mental Health Tracker API v2"}
