import os
import textwrap
from functools import lru_cache
from pathlib import Path

import google.generativeai as genai  # type: ignore

from config import DIALECT_LABELS

DEFAULT_MODEL = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-2.0-flash")
SYSTEM_PROMPT = textwrap.dedent(
    """
    คุณคือครูสอนสำเนียงไทย ให้ข้อเสนอแนะสั้นๆ ช่วยผู้เรียนออกเสียงให้ถูกต้อง
    - อธิบายสิ่งที่พูดถูกต้อง/ใกล้เคียง
    - แนะนำคำ/พยางค์ที่ต้องแก้ พร้อมสำเนียงที่ถูก
    - ใช้ภาษาที่ให้กำลังใจ
    """
).strip()

ROLEPLAY_TRAITS = {
    "central": "พูดสุภาพเป็นกันเองแบบคนกรุงเทพ แต่ไม่เป็นทางการจนเกินไป",
    "northern": "ใช้สำเนียงและคำเมืองจริง น้ำเสียงนุ่มนวล อบอุ่น",
    "isan": "ใช้คำพูดอีสาน สนุก อัธยาศัยดี และชวนคุย",
    "southern": "พูดรวดเร็ว แต่เป็นมิตร แทรกคำลงท้ายแบบใต้",
}


@lru_cache
def _load_api_key() -> str:
    key = os.getenv("GOOGLE_API_KEY")
    if key:
        return key
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if not line or line.strip().startswith("#"):
                continue
            if "GOOGLE_API_KEY" in line:
                _, _, value = line.partition("=")
                value = value.strip().strip('"').strip("'")
                if value:
                    return value
    raise RuntimeError("GOOGLE_API_KEY not found in environment or project .env")


@lru_cache
def _get_model():
    api_key = _load_api_key()
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(DEFAULT_MODEL)


def suggest_feedback(text: str, dialect: str) -> str:
    model = _get_model()
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"ผู้เรียนพูดว่า: {text}\n"
        f"สำเนียง: {dialect}"
    )
    try:
        resp = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.4,
                max_output_tokens=256,
            ),
        )
    except Exception as exc:  # broad catch to bubble clean message
        raise RuntimeError(f"Gemini feedback request failed: {exc}") from exc
    feedback = (resp.text or "").strip()
    if not feedback:
        raise RuntimeError("Gemini did not return any feedback text")
    return feedback


def _history_to_text(history):
    if not history:
        return "–"
    lines = []
    for speaker, message in history:
        clean = str(message).strip()
        if not clean:
            continue
        if speaker == "คุณ":
            speaker_label = "ผู้เรียน"
        else:
            speaker_label = speaker
        lines.append(f"{speaker_label}: {clean}")
    return "\n".join(lines) if lines else "–"


def roleplay_response(message: str, dialect: str, history=None) -> str:
    """
    Let Gemini role-play as a local speaker from the selected dialect.
    """
    model = _get_model()
    persona = ROLEPLAY_TRAITS.get(dialect, "พูดเป็นกันเองกับผู้เรียน")
    region = DIALECT_LABELS.get(dialect, dialect)
    history_text = _history_to_text(history)
    prompt = textwrap.dedent(
        f"""
        คุณคือชาว {region} ที่กำลังคุยกับผู้เรียนภาษาถิ่นไทย
        - ใช้คำศัพท์ น้ำเสียง และคำลงท้ายของคน {region} จริง
        - บุคลิก: {persona}
        - ตอบไม่เกิน 3 ประโยค
        - ให้กำลังใจ และถ้าเหมาะสม ชวนผู้เรียนตอบกลับ 1 คำถามสั้นๆ

        ประวัติการสนทนาก่อนหน้า:
        {history_text}

        ผู้เรียน: {message.strip()}
        """
    ).strip()

    try:
        resp = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.6,
                max_output_tokens=200,
            ),
        )
    except Exception as exc:
        raise RuntimeError(f"Gemini role-play request failed: {exc}") from exc
    reply = (resp.text or "").strip()
    if not reply:
        raise RuntimeError("Gemini did not return any role-play response")
    return reply
