"""
main.py — FastAPI backend for the Clinic Patient Feedback Auditor.

Pipeline per upload:
  1. Save uploaded audio to disk, insert a `visits` row (status=uploaded)
  2. Kick off transcription in a background thread (STT is CPU/IO heavy,
     so we run it via run_in_executor to avoid blocking the event loop)
  3. Once transcript is ready, run sentiment analysis (2nd pipeline stage)
  4. Store results in MySQL
  5. Broadcast the finished result to all connected dashboard clients
     over a WebSocket — this is what gives the "real-time, no reload"
     behavior the frontend needs.
"""
import os
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import db
from app.stt import transcribe_audio
from app.sentiment import analyze_sentiment

app = FastAPI(title="Clinic Patient Feedback Auditor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

executor = ThreadPoolExecutor(max_workers=4)

# --- WebSocket connection manager (for real-time dashboard pushes) ---
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        for ws in list(self.active):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def process_pipeline(visit_id: int, filepath: str):
    """Runs the two pipeline stages off the event loop, then persists +
    broadcasts the result."""
    loop = asyncio.get_event_loop()

    # Stage 1: Speech-to-text (blocking work -> thread pool)
    transcript = await loop.run_in_executor(executor, transcribe_audio, filepath)
    db.update_transcript(visit_id, transcript)

    # Stage 2: Sentiment analysis (fast, but kept as a distinct async step)
    label, score = await loop.run_in_executor(executor, analyze_sentiment, transcript)
    db.insert_sentiment(visit_id, label, score)

    # Push the result to every connected dashboard
    await manager.broadcast({
        "visit_id": visit_id,
        "transcript": transcript,
        "sentiment": label,
        "score": score,
    })


@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1] or ".webm"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, unique_name)

    with open(filepath, "wb") as f:
        f.write(await file.read())

    visit_id = db.insert_visit(unique_name)

    # Fire-and-forget: don't make the client wait for STT + sentiment to
    # finish. The result arrives later over the WebSocket.
    asyncio.create_task(process_pipeline(visit_id, filepath))

    return {"visit_id": visit_id, "status": "processing"}


@app.get("/feed")
async def get_feed():
    """Lets the dashboard load recent history on page load."""
    return db.fetch_feed()


# Serve the frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")
