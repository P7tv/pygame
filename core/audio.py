# โมดูล core/audio.py
# รวบรวมเครื่องมือด้านเสียงทั้งการบันทึกไมค์และการส่งงานให้โมเดลรู้จำเสียง
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
    """โปรเซสลูกที่คอยโหลดโมเดลและถอดเสียง แยกจาก UI หลัก"""
    # โหลดไลบรารีหนัก ๆ ในโปรเซสลูกเพื่อไม่ให้บล็อก UI หลัก
    # นำเข้าไลบรารีหนักเฉพาะใน worker เพื่อลดเวลาบูตของโปรเซสหลัก
    try:
        from transformers import pipeline
        import torch
    except Exception as e:
        status_q.put(("error", f"worker import error: {e}"))
        return

    model = None  # โหลดเฉพาะเมื่อจำเป็นครั้งแรกแล้วเก็บไว้ใช้ซ้ำใน worker

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
        # วนรอคำสั่งจากโปรเซสหลักผ่านคิว
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
            # รับงานถอดเสียง: ถ้ายังไม่ได้โหลดโมเดลให้โหลดก่อน
            job_id, path = cmd[1], cmd[2]
            if model is None:
                # หากยังไม่โหลด ให้โหลดแบบ lazy
                load_model()
                if model is None:
                    res_q.put((job_id, None, "failed"))
                    continue
            try:
                status_q.put(("status", "transcribing"))
                result = model(path)
                text = result.get("text", "").strip() if isinstance(result, dict) else str(result)
                # ส่งผลลัพธ์กลับผ่าน result queue พร้อมอัปเดตสถานะ
                res_q.put((job_id, text, "ok"))
                status_q.put(("status", "done"))
                status_q.put(("status", "loaded"))
            except Exception as exc:
                res_q.put((job_id, None, f"error: {exc}"))
                status_q.put(("error", f"transcribe error: {exc}"))
        else:
            # คำสั่งไม่รู้จัก
            status_q.put(("error", f"unknown cmd: {op}"))


class Recorder:
    def __init__(self, samplerate=SAMPLE_RATE, channels=CHANNELS, max_seconds=MAX_SPEAK_SECONDS):
        """เซ็ตอัปพารามิเตอร์การอัดเสียงและเตรียมบัฟเฟอร์เฟรม"""
        self.samplerate = samplerate
        self.channels = channels
        self.max_seconds = max_seconds
        self.frames = []
        self.recording = False
        self.stream = None

    def start(self):
        """เริ่มต้นเปิด stream จาก sounddevice แล้วปล่อย callback เก็บเฟรม"""
        print("[ASR] Recording...")
        self.frames = []
        self.recording = True
        sd.default.samplerate = self.samplerate
        sd.default.channels = self.channels
        self.stream = sd.InputStream(callback=self.callback)
        self.stream.start()

    def callback(self, indata, frames, time_info, status):
        """callback ที่ sounddevice เรียกเมื่อมีตัวอย่างเสียงใหม่"""
        if self.recording:
            self.frames.append(indata.copy())

    def stop_to_wav(self):
        """หยุดสตรีมแล้วรวมเฟรมเป็นไฟล์ WAV ชั่วคราวสำหรับส่งให้ ASR"""
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
    """ตัวจัดการ ASR ที่คุยกับ worker process เพื่อโหลดโมเดลและถอดเสียง

    API หลัก:
    - start_loading(): เรียกให้ worker โหลดโมเดลล่วงหน้า
    - request_transcribe(path): ส่งงานถอดเสียงและคืน job id
    - poll(): ดึงผลลัพธ์/สถานะจากคิวมาเก็บใน dictionary ภายใน
    - get_result(job_id): คืนสถานะ+ข้อความของงานตาม id
    - get_status(): แจ้งสถานะล่าสุดของ worker/โมเดล
    - shutdown(): ปิด worker อย่างสุภาพ
    """
    _instance = None

    def __new__(cls):
        """บังคับให้คลาสนี้มีอินสแตนซ์เดียวตลอดอายุการทำงาน"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """เตรียม queue/worker state และ cache สถานะล่าสุด"""
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self.cmd_q = Queue()      # คิวส่งคำสั่งไป worker
        self.res_q = Queue()      # คิวรับผลลัพธ์ข้อความกลับ
        self.status_q = Queue()   # คิวสถานะแจ้งผู้ใช้
        self.proc = None
        self.job_counter = 0
        self.completed = {}  # เก็บ mapping job_id -> (สถานะ, ข้อความ)
        self.last_status = "idle"

    def _ensure_process(self):
        """ตรวจสอบว่า worker ยังทำงานอยู่ ถ้าไม่ให้สร้างใหม่"""
        if self.proc is None or not self.proc.is_alive():
            self.proc = Process(target=_asr_worker, args=(self.cmd_q, self.res_q, self.status_q), daemon=True)
            self.proc.start()
            time.sleep(0.05)

    def start_loading(self):
        """สั่งให้ worker โหลดโมเดลในเบื้องหลัง"""
        self._ensure_process()
        self.cmd_q.put(("load",))

    def request_transcribe(self, path: str):
        """รับ path ไฟล์เสียงแล้วส่งคำขอถอดเสียง (คืน job id ทันที)"""
        self._ensure_process()
        self.job_counter += 1
        job_id = self.job_counter
        self.cmd_q.put(("transcribe", job_id, path))
        # จดจำว่างานนี้กำลังรอผล
        self.completed[job_id] = ("pending", None)
        return job_id

    def poll(self):
        """ตรวจสอบคิวผลลัพธ์/สถานะเพื่ออัปเดต state ภายใน"""
        # ดึงผลลัพธ์ที่ worker ส่งกลับ (แบบไม่บล็อก)
        try:
            while True:
                job_id, text, status = self.res_q.get_nowait()
                if status == "ok":
                    self.completed[job_id] = ("ok", text)
                else:
                    # กรณีผิดพลาดเก็บข้อความ error แทน
                    self.completed[job_id] = ("error", str(status))
        except Exception:
            pass
        # เก็บข้อความสถานะทั่วไป เช่น loading/transcribing
        try:
            while True:
                msg_type, msg = self.status_q.get_nowait()
                if msg_type == "status":
                    self.last_status = msg
                else:
                    # หากเป็น error นำหน้าด้วยประเภทเพื่อ debug ง่าย
                    self.last_status = msg_type + ": " + str(msg)
        except Exception:
            pass

    def get_result(self, job_id):
        """คืนสถานะกับข้อความของงาน หากยังไม่เสร็จให้ status เป็น pending"""
        self.poll()
        return self.completed.get(job_id, ("pending", None))

    def get_status(self):
        """ให้สถานะล่าสุดของ worker (โหลดอยู่, ถอดเสียง, พร้อม ฯลฯ)"""
        self.poll()
        return self.last_status

    def shutdown(self):
        """พยายามปิด worker process อย่างสุภาพเมื่อเกมจบ"""
        try:
            if self.proc and self.proc.is_alive():
                self.cmd_q.put(("shutdown",))
                self.proc.join(timeout=1.0)
        except Exception:
            pass
