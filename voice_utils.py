"""
Voice utilities for speech recognition and text-to-speech
Provides mic() and speak() functions for voice interaction
"""

import os
import sys
import json
import logging
import vosk
import sounddevice as sd
import pyttsx3
import threading
import time
import queue

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class SpeechRecognizer:
    """Speech recognizer using Vosk and SoundDevice for dictation mode."""

    def __init__(self, model_path: str, sample_rate: int = 16000):
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.dictation_running = False
        self.dictation_text = []
        self._dictation_thread = None
        self.model = self._load_model()

    def _load_model(self):
        """Validates and loads the Vosk model."""
        if not os.path.isdir(self.model_path):
            logging.error(f"Model path not found: {self.model_path}")
            raise FileNotFoundError(f"Vosk model not found at: {self.model_path}")
        
        try:
            logging.info(f"Loading Vosk model from: {self.model_path}")
            model = vosk.Model(self.model_path)
            logging.info("Vosk model loaded successfully.")
            return model
        except Exception as e:
            logging.exception("Failed to load model:")
            raise

    def start_dictation(self):
        """Starts listening and buffering voice in a background thread."""
        if self.dictation_running:
            logging.warning("Dictation already running.")
            return False

        logging.info("🎙️ Dictation started. Listening...")
        self.dictation_running = True
        self.dictation_text = []
        self._dictation_thread = threading.Thread(target=self._dictation_loop, daemon=True)
        self._dictation_thread.start()
        return True

    def _dictation_loop(self):
        """Background thread that captures audio and converts to text."""
        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate, 
                blocksize=8000, 
                dtype='int16',
                channels=1
            ) as stream:
                recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)
                
                while self.dictation_running:
                    data, _ = stream.read(4000)
                    data_bytes = bytes(data)

                    if recognizer.AcceptWaveform(data_bytes):
                        result = json.loads(recognizer.Result())
                        text = result.get("text", "").strip()
                        if text:
                            self.dictation_text.append(text)
                            logging.info(f"🗣️ Captured: {text}")

        except Exception as e:
            logging.exception("Dictation error:")
            self.dictation_running = False

    def stop_dictation(self) -> str:
        """Stops dictation and returns the captured text."""
        if not self.dictation_running:
            return ""

        logging.info("🛑 Stopping dictation...")
        self.dictation_running = False
        
        if self._dictation_thread and self._dictation_thread.is_alive():
            self._dictation_thread.join(timeout=2)

        final_text = " ".join(self.dictation_text)
        logging.info(f"📝 Final text: {final_text}")
        return final_text

    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self.dictation_running


class TextToSpeech:
    """Text-to-speech engine using pyttsx3 with proper thread safety."""

    def __init__(self, gender='female', rate=150, volume=1.0):
        self.gender = gender
        self.rate = rate
        self.volume = volume
        self.speak_queue = queue.Queue()
        self.is_running = False
        self._start_engine_thread()

    def _start_engine_thread(self):
        """Start a dedicated thread for TTS engine."""
        self.is_running = True
        self.engine_thread = threading.Thread(target=self._engine_loop, daemon=True)
        self.engine_thread.start()

    def _engine_loop(self):
        """Main loop for TTS engine - runs in dedicated thread."""
        # Initialize engine in this thread
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        
        # Set gender
        selected = None
        for voice in voices:
            if self.gender.lower() in voice.name.lower():
                selected = voice.id
                break
        
        if selected:
            engine.setProperty('voice', selected)
        else:
            logging.warning(f"No {self.gender} voice found. Using default.")
        
        engine.setProperty('rate', self.rate)
        engine.setProperty('volume', self.volume)
        
        # Process speech queue
        while self.is_running:
            try:
                text = self.speak_queue.get(timeout=0.5)
                if text:
                    # Remove URLs from speech
                    import re
                    clean_text = re.sub(
                        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', 
                        'link provided', text
                    )
                    engine.say(clean_text)
                    engine.runAndWait()
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"TTS error: {e}")

    def speak(self, text: str):
        """Add text to speech queue."""
        if not text.strip():
            logging.warning("No text provided to speak.")
            return
        self.speak_queue.put(text)

    def stop(self):
        """Stop the TTS engine."""
        self.is_running = False
        if self.engine_thread.is_alive():
            self.engine_thread.join(timeout=1)


# Global instances
_recognizer_instance = None
_tts_instance = None


def initialize_voice_system(model_path: str):
    """Initialize the voice system with the Vosk model path."""
    global _recognizer_instance, _tts_instance
    
    if _recognizer_instance is None:
        _recognizer_instance = SpeechRecognizer(model_path)
    
    if _tts_instance is None:
        _tts_instance = TextToSpeech(gender='female', rate=160, volume=1.0)
    
    return _recognizer_instance, _tts_instance


def start_recording() -> bool:
    """Start recording from microphone."""
    global _recognizer_instance
    
    if _recognizer_instance is None:
        raise RuntimeError("Voice system not initialized. Call initialize_voice_system() first.")
    
    return _recognizer_instance.start_dictation()


def stop_recording() -> str:
    """Stop recording and return the recognized text."""
    global _recognizer_instance
    
    if _recognizer_instance is None:
        raise RuntimeError("Voice system not initialized. Call initialize_voice_system() first.")
    
    return _recognizer_instance.stop_dictation()


def is_recording() -> bool:
    """Check if microphone is currently recording."""
    global _recognizer_instance
    if _recognizer_instance:
        return _recognizer_instance.is_recording()
    return False


def speak(text: str):
    """Speak the given text using female voice."""
    global _tts_instance
    
    if _tts_instance is None:
        raise RuntimeError("Voice system not initialized. Call initialize_voice_system() first.")
    
    _tts_instance.speak(text)


# Legacy function for compatibility
def mic(timeout: int = 10) -> str:
    """
    Start listening to microphone and return recognized text.
    This is kept for backward compatibility but not recommended.
    Use start_recording() and stop_recording() instead.
    """
    global _recognizer_instance
    
    if _recognizer_instance is None:
        raise RuntimeError("Voice system not initialized. Call initialize_voice_system() first.")
    
    _recognizer_instance.start_dictation()
    time.sleep(timeout)
    return _recognizer_instance.stop_dictation()


if __name__ == "__main__":
    # Test the voice utilities
    model_path = r"D:\Satyam\personal_learning\future_projects\jarvis_desk_assist\jarvis_desk_bot\models\voice_models\vosk-model-small-en-us-0.15"
    
    try:
        initialize_voice_system(model_path)
        
        speak("Hello! Testing voice system.")
        
        print("Starting recording... Press Enter to stop")
        start_recording()
        input()  # Wait for user to press Enter
        
        user_text = stop_recording()
        print(f"You said: {user_text}")
        
        speak(f"You said: {user_text}")
        time.sleep(3)  # Wait for speech to finish
        
    except Exception as e:
        print(f"Error: {e}")