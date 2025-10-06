# asr.py
import queue, tempfile, time
import numpy as np
import sounddevice as sd, soundfile as sf
from transformers import pipeline

class Recorder:
    def __init__(self, rate=16000, ch=1, max_seconds=6.0):
        self.rate, self.ch, self.max_seconds = rate, ch, max_seconds
        self.q = queue.Queue()
        self.frames = []
        self.stream = None
        self.rec = False
        self.t0 = 0.0

    def _cb(self, indata, frames, time_info, status):
        if self.rec:
            self.q.put(indata.copy())
            if time.time() - self.t0 >= self.max_seconds:
                self.rec = False

    def start(self):
        self.frames.clear()
        self.rec = True
        self.t0 = time.time()
        self.stream = sd.InputStream(
            samplerate=self.rate, channels=self.ch, dtype="float32",
            callback=self._cb, blocksize=1024)
        self.stream.start()

    def stop_to_wav(self):
        self.rec = False
        if self.stream:
            self.stream.stop(); self.stream.close(); self.stream = None
        while not self.q.empty():
            self.frames.append(self.q.get())
        audio = np.concatenate(self.frames, axis=0) if self.frames else np.zeros((1,self.ch), dtype="float32")
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        sf.write(tmp.name, audio, self.rate)
        return tmp.name


class PathummaASR:
    def __init__(self, device="cpu"):
        # โหลดโมเดล Pathumma
        print("[ASR] Loading NECTEC Pathumma whisper model...")
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model="nectec/Pathumma-whisper-th-large-v3",
            device=0 if device == "cuda" else -1
        )

    def transcribe(self, wav_path: str) -> str:
        try:
            result = self.pipe(wav_path)
            if isinstance(result, dict) and "text" in result:
                # ลบการเว้นวรรคทั้งหมดออกจากผลลัพธ์
                return result["text"].strip().replace(" ", "")
            return ""
        except Exception as e:
            print("ASR error:", e)
            return ""
