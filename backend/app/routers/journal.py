from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app import schemas, models
from app.database import get_db
from app.dependencies import get_current_user

router = APIRouter(
    prefix="/journals",
    tags=["Journals"]
)

@router.get("/", response_model=List[schemas.Journal])
def get_journals(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Journal).filter(models.Journal.user_id == current_user.id).all()

from app.utils import analyze_sentiment

@router.post("/", response_model=schemas.Journal)
def create_journal(journal: schemas.JournalCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Auto-analyze sentiment
    sentiment = analyze_sentiment(journal.content)
    
    # Handle custom date/time
    created_at = datetime.utcnow()
    if journal.entry_date:
        try:
            d = datetime.strptime(journal.entry_date, "%Y-%m-%d").date()
            t = datetime.strptime(journal.entry_time, "%H:%M").time() if journal.entry_time else datetime.min.time()
            created_at = datetime.combine(d, t)
        except ValueError:
            pass # Fallback to now if format is wrong
            
    new_journal = models.Journal(
        content=journal.content,
        user_id=current_user.id,
        mood_score=sentiment["score"],
        sentiment_label=sentiment["label"],
        created_at=created_at
    )
    db.add(new_journal)
    db.commit()
    db.refresh(new_journal)
    return new_journal

@router.get("/{journal_id}", response_model=schemas.Journal)
def get_journal(journal_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    journal = db.query(models.Journal).filter(models.Journal.id == journal_id, models.Journal.user_id == current_user.id).first()
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    return journal

@router.delete("/{journal_id}")
def delete_journal(journal_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    journal = db.query(models.Journal).filter(models.Journal.id == journal_id, models.Journal.user_id == current_user.id).first()
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    
    db.delete(journal)
    db.commit()
    return {"message": "Journal deleted successfully"}

@router.put("/{journal_id}", response_model=schemas.Journal)
def update_journal(journal_id: int, journal_update: schemas.JournalCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    journal = db.query(models.Journal).filter(models.Journal.id == journal_id, models.Journal.user_id == current_user.id).first()
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    
    journal.content = journal_update.content
    
    # Re-analyze sentiment since content changed
    sentiment = analyze_sentiment(journal.content)
    journal.mood_score = sentiment["score"]
    journal.sentiment_label = sentiment["label"]
    
    db.commit()
    db.refresh(journal)
    return journal

from app.services.llm import generate_wellness_report
from datetime import datetime, timedelta

def generate_insights_logic(days: int, db: Session, current_user: models.User):
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Fetch entries
    entries = db.query(models.Journal).filter(
        models.Journal.user_id == current_user.id,
        models.Journal.created_at >= cutoff_date
    ).all()
    
    if not entries:
        return {"report": f"No journal entries found for the last {days} days. Start writing to get insights!"}
    
    # Extract text content
    text_content = [e.content for e in entries]
    
    # Generate report using LLM
    report = generate_wellness_report(text_content)
    
    return {"report": report, "period": f"Last {days} days", "entries_analyzed": len(entries)}

@router.get("/insights/report")
def get_custom_insights(period: str = "7d", db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Generate a report for the user based on journals from the last 'period' days (e.g. '7d', '30d').
    """
    days = 30 if period == "30d" else 7
    return generate_insights_logic(days, db, current_user)

@router.get("/insights/weekly")
def get_weekly_insights(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Generate a Weekly wellness report (Last 7 Days).
    """
    return generate_insights_logic(7, db, current_user)

@router.get("/insights/monthly")
def get_monthly_insights(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    Generate a Monthly wellness report (Last 30 Days).
    """
    return generate_insights_logic(30, db, current_user)
