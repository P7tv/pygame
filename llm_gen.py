import json, os, re, textwrap
from pathlib import Path

import google.generativeai as genai  # type: ignore

from config import DIALECTS

def _resolve_google_api_key() -> str:
    key = os.getenv("GOOGLE_API_KEY")
    if key:
        return key
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if not line or line.strip().startswith("#"):
                continue
            if "GOOGLE_API_KEY" not in line:
                continue
            _, _, value = line.partition("=")
            value = value.strip().strip('"').strip("'")
            if value:
                return value
    raise RuntimeError("GOOGLE_API_KEY not found in environment or .env file")

API_KEY = None
MODEL = None
_model = None

API_KEY = _resolve_google_api_key()
MODEL = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-2.5-flash")
genai.configure(api_key=API_KEY)
_model = genai.GenerativeModel(model_name=MODEL)

def _extract_json(s: str) -> str:
    m = re.search(r"\[[\s\S]*\]", s)
    return m.group(0) if m else s

def generate(topic: str, n: int = 8):
    if _model is None:
        raise RuntimeError("Gemini model is not configured")
    # Prompt แนว Duolingo: กะทัดรัด ชัดเจน และชวนให้พูดออกเสียง
    system = textwrap.dedent(f"""
    คุณคือผู้ออกแบบบทเรียนสไตล์ Duolingo สำหรับเกมฝึกพูดภาษาถิ่นไทย โฟกัสโหมด "พูดล้วน"
    แนวทางสำคัญ:
    - คืนค่าเป็น JSON เท่านั้น (ห้ามมีคำบรรยายเพิ่มเติมหรือโค้ดบล็อก)
    - สร้าง prompt ไม่เกิน 60 ตัวอักษร ใช้น้ำเสียงกระตุ้นให้ฝึกพูดแบบสนุก เป็นกันเอง
    - แทรกหัวข้อที่ได้รับลงใน prompt โดยตรง (ห้ามใช้สัญลักษณ์ปีกกา {{ }})
    - targets ของแต่ละภาคต้องเป็นคำศัพท์หรือวลีสั้นที่คนท้องถิ่นใช้จริงเกี่ยวกับหัวข้อ (ไม่ใช่ประโยคยาว)
    - ให้แต่ละ dialect มี 2 หรือ 3 คำ ไม่เว้นวรรคแปลกๆ ในคำภาษาไทย
    - หากคำศัพท์ของภาคไหนตรงกับภาษากลาง ให้เลือกคำที่ชาวบ้านใช้จริงหรือคำเรียกเฉพาะถิ่น
    ตัวอย่าง (หัวข้อ "{topic}"):
    [
      {{
        "prompt": "พูดคำท้องถิ่นที่ใช้บ่อยเกี่ยวกับ {topic}",
        "targets": {{
          "central": ["ทำ", "พูด", "กิน"],
          "northern": ["ยะ", "ฮ้อง", "กิ๋น"],
          "isan": ["เฮ็ด", "เว้า", "กิน"],
          "southern": ["ทํา", "แหลง", "กินข้าว"]
        }}
      }}
    ]
    สร้างโจทย์ {n} ข้อ โดยทุกข้อเชื่อมโยงกับหัวข้อ '{topic}'
    """)
    user = f"สร้างบทเรียน {n} ข้อ สำหรับหัวข้อ: {topic}"

    prompt = f"{system}\n\n{user}"
    resp = _model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=2048,
            response_mime_type="application/json",
        ),
    )
    raw_text = resp.text
    if not raw_text:
        for cand in getattr(resp, "candidates", []):
            for part in getattr(getattr(cand, "content", None), "parts", []):
                text = getattr(part, "text", None)
                if text:
                    raw_text = text
                    break
            if raw_text:
                break
    raw = (raw_text or "").strip()
    if not raw:
        raise ValueError("Gemini response is empty")
    data = json.loads(_extract_json(raw))

    # เพิ่ม dialect ที่ขาดให้ครบ
    for it in data:
        tg = it.setdefault("targets", {})
        for d in DIALECTS:
            tg.setdefault(d, tg.get("central", []))
    return data
