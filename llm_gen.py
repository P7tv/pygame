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

RETRYABLE_FINISH_REASONS = {"MAX_TOKENS"}
MAX_ATTEMPTS = 3


def _parse_response(resp):
    raw_text = None
    finish_reasons = []
    safety_hits = []
    for cand in getattr(resp, "candidates", []) or []:
        finish = getattr(cand, "finish_reason", None)
        if finish is not None:
            finish_name = (
                finish.name if hasattr(finish, "name") else str(finish)
            )
            finish_reasons.append(finish_name)
        ratings = getattr(cand, "safety_ratings", None) or []
        if ratings:
            safety_hits.append(
                ", ".join(
                    f"{getattr(r, 'category', 'unknown')}={getattr(r, 'probability', 'unknown')}"
                    for r in ratings
                )
            )
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []):
            text = getattr(part, "text", None)
            if text:
                raw_text = text
                break
        if raw_text:
            break
    return raw_text, finish_reasons, safety_hits


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
    attempt = 0
    max_tokens = 2048
    last_finish = []
    last_safety = []
    raw_text = None
    while attempt < MAX_ATTEMPTS:
        resp = _model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
            ),
        )
        raw_text, finish_reasons, safety_hits = _parse_response(resp)
        if raw_text:
            break
        last_finish = finish_reasons
        last_safety = safety_hits
        attempt += 1
        retryable = any(
            reason in RETRYABLE_FINISH_REASONS for reason in finish_reasons
        )
        if retryable and "MAX_TOKENS" in finish_reasons:
            max_tokens = min(max_tokens + 1024, 4096)
            continue
        else:
            break
    if raw_text is None:
        reason_msg = ", ".join(last_finish) if last_finish else "NONE"
        safety_msg = "; ".join(last_safety) if last_safety else "NONE"
        raise RuntimeError(
            "Gemini response contains no text "
            f"(finish_reason={reason_msg}; safety={safety_msg})"
        )
    raw = raw_text.strip()
    if not raw:
        raise ValueError("Gemini response is empty")
    data = json.loads(_extract_json(raw))

    # เพิ่ม dialect ที่ขาดให้ครบ
    for it in data:
        tg = it.setdefault("targets", {})
        for d in DIALECTS:
            tg.setdefault(d, tg.get("central", []))
    return data
