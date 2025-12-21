from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def analyze_sentiment(text: str):
    """
    Analyze text sentiment using VADER.
    Returns a dict with 'compound' score and 'label'.
    Compound score ranges from -1 (Most Negative) to +1 (Most Positive).
    """
    scores = analyzer.polarity_scores(text)
    compound = scores['compound']
    
    if compound >= 0.05:
        label = "Positive"
    elif compound <= -0.05:
        label = "Negative"
    else:
        label = "Neutral"
        
    return {
        "score": compound,
        "label": label,
        "details": scores
    }
