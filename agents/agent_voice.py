import os
import queue
import threading
from io import BytesIO


def _play_elevenlabs(message: str, api_key: str, voice_id: str):
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import play
        client = ElevenLabs(api_key=api_key)
        audio  = client.text_to_speech.convert(
            voice_id=voice_id,
            text=message,
            model_id="eleven_monolingual_v1",
            voice_settings={"stability": 0.5, "similarity_boost": 0.75},
        )
        play(audio)
        return True
    except Exception as e:
        print(f"[VoiceAgent] ElevenLabs failed: {e}")
        return False


def _play_pyttsx3(message: str):
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 165)
        engine.say(message)
        engine.runAndWait()
        engine.stop()
        return True
    except Exception as e:
        print(f"[VoiceAgent] pyttsx3 failed: {e}")
        return False


class VoiceAgent:
    def __init__(self):
        self._api_key  = os.getenv("ELEVENLABS_API_KEY")
        self._voice_id = os.getenv("ELEVENLABS_VOICE_ID", "Rachel")
        self._enabled = True
        self._queue: queue.Queue[str] = queue.Queue()
        self._lock = threading.Lock()
        self._is_speaking = False
        self._worker = threading.Thread(target=self._run_worker, daemon=True)
        self._worker.start()

    def set_enabled(self, enabled: bool):
        self._enabled = bool(enabled)

    def set_voice_id(self, voice_id: str):
        if voice_id:
            self._voice_id = voice_id

    def get_settings(self) -> dict:
        return {
            "enabled": self._enabled,
            "voice_id": self._voice_id,
            "is_speaking": self._is_speaking,
            "queued_messages": self._queue.qsize(),
        }

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "recording.webm", language_code: str | None = None) -> dict:
        if not self._api_key:
            raise RuntimeError("ELEVENLABS_API_KEY is required for transcription.")

        try:
            from elevenlabs.client import ElevenLabs
        except Exception as exc:
            raise RuntimeError("ElevenLabs SDK is unavailable for transcription.") from exc

        client = ElevenLabs(api_key=self._api_key)
        audio_stream = BytesIO(audio_bytes)
        audio_stream.name = filename

        transcription = client.speech_to_text.convert(
            file=audio_stream,
            model_id="scribe_v2",
            language_code=language_code or None,
            diarize=False,
            tag_audio_events=False,
        )

        text = getattr(transcription, "text", None)
        language = getattr(transcription, "language_code", None)
        words = getattr(transcription, "words", None)

        return {
            "text": text or "",
            "language_code": language,
            "word_count": len(words) if words else 0,
            "filename": filename,
        }

    def speak(self, message: str, blocking: bool = False) -> dict:
        """Queue speech so multiple messages never overlap."""
        print(f"[VoiceAgent] {message}")

        if not self._enabled:
            return {"status": "muted"}

        if blocking:
            self._play_message(message)
            return {"status": "spoken"}

        self._queue.put(message)
        return {"status": "queued", "queued_messages": self._queue.qsize()}

    def _run_worker(self):
        while True:
            message = self._queue.get()
            try:
                if self._enabled:
                    self._play_message(message)
            finally:
                self._queue.task_done()

    def _play_message(self, message: str):
        with self._lock:
            self._is_speaking = True
            try:
                if self._api_key:
                    if _play_elevenlabs(message, self._api_key, self._voice_id):
                        return
                _play_pyttsx3(message)
            finally:
                self._is_speaking = False
