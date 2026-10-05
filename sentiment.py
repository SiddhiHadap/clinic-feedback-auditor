"""
sentiment.py — Sentiment analysis pipeline stage.

Uses TextBlob for simplicity and speed (fine for a screening project;
in production you'd likely swap in a fine-tuned classifier).
Maps TextBlob's polarity (-1.0 to 1.0) into a clear label.
"""
from textblob import TextBlob

POSITIVE_THRESHOLD = 0.1
NEGATIVE_THRESHOLD = -0.1


def analyze_sentiment(text: str) -> tuple[str, float]:
    if not text.strip():
        return "NEUTRAL", 0.0

    polarity = TextBlob(text).sentiment.polarity  # -1.0 .. 1.0

    if polarity > POSITIVE_THRESHOLD:
        label = "POSITIVE"
    elif polarity < NEGATIVE_THRESHOLD:
        label = "NEGATIVE"
    else:
        label = "NEUTRAL"

    return label, round(polarity, 3)
