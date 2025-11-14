# core/audio.py
import os
import tempfile
import wave
import numpy as np
import sounddevice as sd
from multiprocessing import Process, Queue
import multiprocessing
import time

SAMPLE_RATE = 16000
CHANNELS = 1
MAX_SPEAK_SECONDS = 6


def _asr_worker(cmd_q: Queue, res_q: Queue, status_q: Queue):
    """Worker process that loads the model and performs transcription.
    Runs in a separate process to avoid blocking the main UI/process.
   """
    # Import heavy libraries inside worker
    try:
        from transformers import pipeline
        import torch
    except Exception as e:
        status_q.put(("error", f"worker import error: {e}"))
        return

    model = None

    def load_model():
        nonlocal model
        try:
            status_q.put(("status", "loading"))
            model = pipeline(
                "automatic-speech-recognition",
                model="nectec/Pathumma-whisper-th-large-v3",
                device=0 if torch.cuda.is_available() else -1,
            )
            status_q.put(("status", "loaded"))
        except Exception as exc:
            status_q.put(("error", f"load error: {exc}"))
            model = None

    while True:
        try:
            cmd = cmd_q.get()
        except Exception:
            break
        if not cmd:
            continue
        op = cmd[0]
        if op == "shutdown":
            break
        if op == "load":
            if model is None:
                load_model()
            else:
                status_q.put(("status", "loaded"))
        elif op == "transcribe":
            job_id, path = cmd[1], cmd[2]
            if model is None:
                # lazy load if needed
                load_model()
                if model is None:
                    res_q.put((job_id, None, "failed"))
                    continue
            try:
                status_q.put(("status", "transcribing"))
                result = model(path)
                text = result.get("text", "").strip() if isinstance(result, dict) else str(result)
                res_q.put((job_id, text, "ok"))
                status_q.put(("status", "done"))
                status_q.put(("status", "loaded"))
            except Exception as exc:
                res_q.put((job_id, None, f"error: {exc}"))
                status_q.put(("error", f"transcribe error: {exc}"))
        else:
            # unknown command
            status_q.put(("error", f"unknown cmd: {op}"))


class Recorder:
    def __init__(self, samplerate=SAMPLE_RATE, channels=CHANNELS, max_seconds=MAX_SPEAK_SECONDS):
        self.samplerate = samplerate
        self.channels = channels
        self.max_seconds = max_seconds
        self.frames = []
        self.recording = False
        self.stream = None

    def start(self):
        print("[ASR] Recording...")
        self.frames = []
        self.recording = True
        sd.default.samplerate = self.samplerate
        sd.default.channels = self.channels
        self.stream = sd.InputStream(callback=self.callback)
        self.stream.start()

    def callback(self, indata, frames, time_info, status):
        if self.recording:
            self.frames.append(indata.copy())

    def stop_to_wav(self):
        print("[ASR] Stopping record...")
        self.recording = False
        if self.stream:
            try:
                self.stream.stop()
            except Exception:
                pass
        data = np.concatenate(self.frames, axis=0) if self.frames else np.array([])
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes((data * 32767).astype(np.int16).tobytes() if len(data) > 0 else b"")
        print(f"[ASR] Saved temp wav: {tmp.name}")
        return tmp.name


class PathummaASR:
    """ASR manager that talks to a worker process for model loading and transcription.

    Public API:
    - start_loading()
    - request_transcribe(path) -> job_id
    - poll()  # move results from queue into local completed dict
    - get_result(job_id) -> text or None
    - get_status() -> last status string
    - shutdown()
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self.cmd_q = Queue()
        self.res_q = Queue()
        self.status_q = Queue()
        self.proc = None
        self.job_counter = 0
        self.completed = {}  # job_id -> (status, text) where status in {"pending","ok","error"}
        self.last_status = "idle"

    def _ensure_process(self):
        if self.proc is None or not self.proc.is_alive():
            self.proc = Process(target=_asr_worker, args=(self.cmd_q, self.res_q, self.status_q), daemon=True)
            self.proc.start()
            time.sleep(0.05)

    def start_loading(self):
        """Ask worker to load the model in background"""
        self._ensure_process()
        self.cmd_q.put(("load",))

    def request_transcribe(self, path: str):
        """Request transcription; returns job id immediately"""
        self._ensure_process()
        self.job_counter += 1
        job_id = self.job_counter
        self.cmd_q.put(("transcribe", job_id, path))
        # mark pending
        self.completed[job_id] = ("pending", None)
        return job_id

    def poll(self):
        """Poll queues and update internal state (non-blocking)"""
        # collect results
        try:
            while True:
                job_id, text, status = self.res_q.get_nowait()
                if status == "ok":
                    self.completed[job_id] = ("ok", text)
                else:
                    # status contains error message
                    self.completed[job_id] = ("error", str(status))
        except Exception:
            pass
        # collect status messages
        try:
            while True:
                msg_type, msg = self.status_q.get_nowait()
                if msg_type == "status":
                    self.last_status = msg
                else:
                    # error or message
                    self.last_status = msg_type + ": " + str(msg)
        except Exception:
            pass

    def get_result(self, job_id):
        """Return transcription result if ready, else None"""
        self.poll()
        return self.completed.get(job_id, ("pending", None))

    def get_status(self):
        self.poll()
        return self.last_status

    def shutdown(self):
        try:
            if self.proc and self.proc.is_alive():
                self.cmd_q.put(("shutdown",))
                self.proc.join(timeout=1.0)
        except Exception:
            pass
