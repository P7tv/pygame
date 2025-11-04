# core/audio.py
import os
import torch
import sounddevice as sd
import numpy as np
import tempfile
import wave
from transformers import pipeline

SAMPLE_RATE = 16000
CHANNELS = 1
MAX_SPEAK_SECONDS = 6

class Recorder:
    def __init__(self, samplerate=SAMPLE_RATE, channels=CHANNELS, max_seconds=MAX_SPEAK_SECONDS):
        self.samplerate = samplerate
        self.channels = channels
        self.max_seconds = max_seconds
        self.frames = []
        self.recording = False

    def start(self):
        print("[ASR] Recording...")
        self.frames = []
        self.recording = True
        sd.default.samplerate = self.samplerate
        sd.default.channels = self.channels
        self.stream = sd.InputStream(callback=self.callback)
        self.stream.start()

    def callback(self, indata, frames, time, status):
        if self.recording:
            self.frames.append(indata.copy())

    def stop_to_wav(self):
        print("[ASR] Stopping record...")
        self.recording = False
        self.stream.stop()
        data = np.concatenate(self.frames, axis=0)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        with wave.open(tmp.name, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes((data * 32767).astype(np.int16).tobytes())
        print(f"[ASR] Saved temp wav: {tmp.name}")
        return tmp.name


class PathummaASR:
    def __init__(self, device="cpu"):
        print("[ASR] Loading NECTEC Pathumma Whisper model...")
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model="nectec/Pathumma-whisper-th-large-v3",
            device=0 if device == "cuda" and torch.cuda.is_available() else -1
        )
        print("[ASR] Model loaded successfully ✅")

    def transcribe(self, audio_path):
        print(f"[ASR] Transcribing {audio_path} ...")
        result = self.pipe(audio_path)
        text = result["text"].strip()
        print(f"[ASR] → {text}")
        return text
