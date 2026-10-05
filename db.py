"""
db.py — small connection helper around mysql-connector-python.

We keep this separate from main.py so the "data access" concern is
isolated from the "HTTP routing" concern (good practice to mention
in an interview).
"""
import mysql.connector
from mysql.connector import pooling

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your_password_here",   # <-- change to your local MySQL password
    "database": "clinic_feedback",
}

# A small connection pool avoids opening a fresh TCP connection to MySQL
# on every single request.
pool = pooling.MySQLConnectionPool(
    pool_name="clinic_pool",
    pool_size=5,
    **DB_CONFIG,
)


def get_conn():
    return pool.get_connection()


def insert_visit(audio_filename: str) -> int:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO visits (audio_filename, status) VALUES (%s, %s)",
            (audio_filename, "uploaded"),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_transcript(visit_id: int, transcript: str, status: str = "transcribed"):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE visits SET transcript_text = %s, status = %s WHERE id = %s",
            (transcript, status, visit_id),
        )
        conn.commit()
    finally:
        conn.close()


def insert_sentiment(visit_id: int, label: str, score: float):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO sentiment_analysis (visit_id, sentiment_label, polarity_score)
               VALUES (%s, %s, %s)""",
            (visit_id, label, score),
        )
        conn.commit()
    finally:
        conn.close()


def fetch_feed(limit: int = 20):
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM visit_feed LIMIT %s", (limit,))
        return cur.fetchall()
    finally:
        conn.close()
