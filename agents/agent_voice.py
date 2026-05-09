import os
import threading
import tempfile


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

    def speak(self, message: str, blocking: bool = False):
        """Speak message. Runs in background thread by default so it doesn't block the agent loop."""
        print(f"[VoiceAgent] {message}")

        def _run():
            if self._api_key:
                if _play_elevenlabs(message, self._api_key, self._voice_id):
                    return
            _play_pyttsx3(message)

        if blocking:
            _run()
        else:
            threading.Thread(target=_run, daemon=True).start()
