"""
stt.py — Speech-to-Text pipeline stage.

Uses the `speech_recognition` library with Google's free Web Speech API
(no API key needed for light usage — fine for a demo/interview project).
Audio is converted to WAV via pydub first, since the recognizer needs WAV.

This function is written to be run inside a background task / thread
pool so it doesn't block the FastAPI event loop (the assignment
specifically calls out "correct asynchronous handling" as a guardrail).
"""
import speech_recognition as sr
from pydub import AudioSegment
import os

recognizer = sr.Recognizer()


def transcribe_audio(filepath: str) -> str:
    # Convert whatever format was uploaded (webm/mp3/m4a/etc) to WAV
    wav_path = filepath.rsplit(".", 1)[0] + ".wav"
    audio = AudioSegment.from_file(filepath)
    audio.export(wav_path, format="wav")

    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        text = ""  # couldn't understand audio
    except sr.RequestError as e:
        raise RuntimeError(f"Speech recognition service error: {e}")
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)

    return text
