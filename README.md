# Clinic Patient Feedback Auditor

## What this is
A pipeline that takes an uploaded voice memo -> transcribes it -> runs
sentiment analysis -> stores it in MySQL -> pushes the result live to a
browser dashboard over a WebSocket (no page reload).

## Architecture in one sentence
FastAPI receives the upload, does the heavy STT + sentiment work in a
background task (off the event loop, via a thread pool), writes to two
related MySQL tables, then broadcasts the finished result to every
connected browser tab over `/ws`.

## Setup (run these once)

```bash
cd clinic_feedback
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# ffmpeg is required by pydub for audio conversion
# macOS:   brew install ffmpeg
# Ubuntu:  sudo apt install ffmpeg
# Windows: download from ffmpeg.org and add to PATH

mysql -u root -p < app/schema.sql
```

Edit `app/db.py` and set your real MySQL password in `DB_CONFIG`.

## Run it

```bash
uvicorn app.main:app --reload --app-dir .
```

Open http://localhost:8000 — upload a short voice memo (wav/mp3/webm),
watch the sentiment box change color live.

## Suggested one-day build order (~6-7 focused hours)

1. **(30 min) Get MySQL running locally** and run `schema.sql`. Confirm
   with `SHOW TABLES;` that `visits` and `sentiment_analysis` exist.
2. **(45 min) Backend skeleton**: get FastAPI running with just the
   `/upload` route saving files to disk and inserting a `visits` row.
   Test with `curl -F "file=@test.wav" localhost:8000/upload`.
3. **(1 hr) Sentiment stage first** (it's the easier, dependency-light
   piece) — hardcode some sample text through `analyze_sentiment()` in
   a Python shell until you trust the labels.
4. **(1.5 hr) Speech-to-text stage** — this is usually the flakiest
   part (audio format issues, ffmpeg install). Get this working in
   isolation with a test file before wiring it into the pipeline.
5. **(1 hr) Wire the async pipeline + WebSocket broadcast** in
   `main.py`. Test with two browser tabs open — both should update
   when either uploads a file.
6. **(1 hr) Frontend polish** — confirm the color-changing box, live
   transcript, and feed history all work end-to-end.
7. **(30-45 min) Rehearse your explanation** — see below. This matters
   as much as the code for an interview screening.

## Be ready to explain (this is likely graded as much as the code)

- **Why two tables instead of one?** Separation between the upload/
  transcription stage and the analysis stage — lets you re-run
  sentiment analysis later without re-transcribing, and models a
  real pipeline instead of one blob of data.
- **Where is the "async" actually happening?** STT and sentiment run
  via `loop.run_in_executor(...)` in a thread pool, so the FastAPI
  event loop is never blocked while a file transcribes. The `/upload`
  endpoint returns immediately; the real result streams in later via
  the WebSocket — that's the "split pipeline" the assignment asks for.
- **Why WebSocket instead of polling?** True "real-time... without
  manual reload" — the frontend doesn't need to keep asking "are you
  done yet?"; the server pushes the moment it's ready.
- **What would you change for production?** Swap TextBlob for a
  fine-tuned clinical-sentiment model, move audio files to object
  storage (S3) instead of local disk, add auth, and use a real task
  queue (Celery/RQ) instead of `asyncio.create_task` for durability
  across server restarts.
