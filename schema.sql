-- ============================================================
-- Clinic Patient Feedback Auditor — Database Schema
-- ============================================================
-- Design rationale (be ready to explain this to the interviewer):
-- We split the data into TWO tables instead of one flat table:
--   1. visits        -> raw upload + transcription record
--   2. sentiment_analysis -> the analysis result, linked 1-to-1 to a visit
--
-- Why split it?
--   - Separation of concerns: the "transcription" stage and the
--     "sentiment analysis" stage are two distinct pipeline steps
--     (the assignment explicitly calls this out as a guardrail).
--   - If you ever swap sentiment models (e.g. TextBlob -> a fine-tuned
--     classifier), you can re-run analysis and insert new rows into
--     sentiment_analysis without touching the visits table.
--   - Makes it trivial to track multiple analysis runs per visit later
--     (e.g. re-analysis with a new model) without losing history.
-- ============================================================

CREATE DATABASE IF NOT EXISTS clinic_feedback;
USE clinic_feedback;

CREATE TABLE IF NOT EXISTS visits (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    audio_filename  VARCHAR(255)   NOT NULL,
    transcript_text TEXT,
    status          ENUM('uploaded','transcribing','transcribed','failed')
                    NOT NULL DEFAULT 'uploaded',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sentiment_analysis (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    visit_id        INT NOT NULL,
    sentiment_label ENUM('POSITIVE','NEGATIVE','NEUTRAL') NOT NULL,
    polarity_score  FLOAT NOT NULL,       -- -1.0 (angry) to 1.0 (satisfied)
    analyzed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (visit_id) REFERENCES visits(id) ON DELETE CASCADE
);

-- Handy view for the dashboard: one row per visit with its latest sentiment
CREATE OR REPLACE VIEW visit_feed AS
SELECT
    v.id,
    v.audio_filename,
    v.transcript_text,
    v.status,
    s.sentiment_label,
    s.polarity_score,
    v.created_at
FROM visits v
LEFT JOIN sentiment_analysis s ON s.visit_id = v.id
ORDER BY v.created_at DESC;
