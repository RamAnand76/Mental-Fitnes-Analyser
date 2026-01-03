import google.generativeai as genai
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def generate_wellness_report(journal_entries: list[str]) -> str:
    """
    Generates a mental health insight report based on journal entries.
    """
    if not settings.GEMINI_API_KEY:
        return "Gemini API Key is missing. Please configure it in .env"

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Construct prompt
        entries_text = "\n".join([f"- {entry}" for entry in journal_entries])
        prompt = f"""
        You are an empathetic mental health assistant. 
        Analyze the following journal entries from a user over the recent period:
        
        {entries_text}
        
        Please provide a supportive summary that covers:
        1. Observable mood patterns (ups and downs).
        2. recurring themes or stressors.
        3. Gentle, actionable advice for the coming week.
        
        Keep the tone professional yet warm and comforting. 
        Do not diagnose. Limit to 150 words.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini API Error: {type(e).__name__}: {e}")
        return "Sorry, we currently cannot generate insights due to a service connection issue."
