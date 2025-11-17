import json
import os
import re
import textwrap
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Sequence

import google.generativeai as genai  # type: ignore

from config import CONTENT_CATEGORIES, DIALECTS, LESSON_COUNT

DEFAULT_MODEL = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-2.5-flash")


def _find_project_env() -> Path | None:
    here = Path(__file__).resolve()
    for parent in [here.parent, here.parent.parent, here.parent.parent.parent]:
        env_path = parent / ".env"
        if env_path.exists():
            return env_path
    return None


@lru_cache
def _load_api_key() -> str:
    key = os.getenv("GOOGLE_API_KEY")
    if key:
        return key
    env_path = _find_project_env()
    if env_path:
        for line in env_path.read_text().splitlines():
            if not line or line.strip().startswith("#"):
                continue
            if "GOOGLE_API_KEY" in line:
                _, _, value = line.partition("=")
                value = value.strip().strip('"').strip("'")
                if value:
                    return value
    raise RuntimeError("GOOGLE_API_KEY not found in environment or .env")


@lru_cache
def _get_model():
    api_key = _load_api_key()
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(DEFAULT_MODEL)


def _extract_json(text: str) -> str:
    match = re.search(r"\[[\s\S]*\]", text)
    return match.group(0) if match else text


def _category_label(key: str) -> str:
    for cat in CONTENT_CATEGORIES:
        if cat["key"] == key:
            return cat["label"]
    return key


def _ensure_dialects(lessons: List[dict], dialects: Sequence[str]) -> List[dict]:
    output = []
    for lesson in lessons:
        prompt = str(lesson.get("prompt", "")).strip()
        raw_targets = lesson.get("targets") or {}
        targets = {}
        for d in dialects:
            vals = raw_targets.get(d)
            if not isinstance(vals, list) or not vals:
                vals = raw_targets.get("central", [])
            targets[d] = [str(v).strip() for v in vals if str(v).strip()]
        output.append({"prompt": prompt, "targets": targets})
    return output


def generate_lessons(category_key: str, count: int = LESSON_COUNT, dialects: Iterable[str] = DIALECTS) -> List[dict]:
    """
    Generate lesson cards for the selected category using Gemini.
    """
    model = _get_model()
    dialects = list(dialects)
    category_label = _category_label(category_key)
    instructions = textwrap.dedent(
        f"""
        คุณคือผู้ออกแบบบทเรียนเสียงสำเนียงไทยสำหรับเกมแนว Duolingo
        - หมวดหมู่บทเรียน: "{category_label}"
        - สร้างบทเรียน {count} ข้อในรูปแบบ JSON array เท่านั้น
        - แต่ละบทเรียนต้องมีฟิลด์ "prompt" (เป็นประโยคชวนพูดสั้น ๆ ภาษาไทย) และ "targets"
        - "targets" คือ map ของสำเนียง: {", ".join(dialects)}
        - targets ของแต่ละภาคเป็น list 2-3 คำ/วลีสั้น ที่เกี่ยวข้องกับหมวดหมู่ และสะท้อนภาษาถิ่นจริง
        - ห้ามให้คำแปลภาษาอังกฤษ หรือคำอธิบายยาวนอกเหนือ JSON
        - ใช้โทนสนุก เป็นกันเอง และชวนให้ผู้เล่นพูดออกเสียง
        - ทุก prompt ต้องกล่าวถึงหมวดหมู่ "{category_label}" หรือสถานการณ์ที่สอดคล้อง

        ตัวอย่างโครงสร้างที่ต้องการ:
        [
          {{
            "prompt": "ลองทักทายแบบคนอีสานดูหน่อย!",
            "targets": {{
              "central": ["สวัสดีครับ", "สวัสดีค่ะ"],
              "northern": ["สวัสดีเจ้า", "สวัสดีครับเจ้า"],
              "isan": ["สวัสดีเด้อ", "เด้อ สวัสดี"],
              "southern": ["หวัดดีแรง", "สวัสดีแรง"]
            }}
          }}
        ]
        """
    ).strip()

    try:
        response = model.generate_content(
            instructions,
            generation_config=genai.types.GenerationConfig(
                temperature=0.25,
                max_output_tokens=2048,
                response_mime_type="application/json",
            ),
        )
    except Exception as exc:  # expose clearer message to caller
        raise RuntimeError(f"Gemini lesson generation failed: {exc}") from exc

    raw_text = (response.text or "").strip()
    if not raw_text:
        raise RuntimeError("Gemini returned empty lesson data")
    try:
        data = json.loads(_extract_json(raw_text))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Gemini returned invalid JSON: {exc}") from exc
    if not isinstance(data, list) or not data:
        raise RuntimeError("Gemini response does not contain lesson list")
    cleaned = _ensure_dialects(data, dialects)
    return cleaned[:count]


def save_lessons(path: str, lessons: Sequence[dict]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(lessons), f, ensure_ascii=False, indent=2)


def generate(category: str, n: int = LESSON_COUNT) -> List[dict]:
    """
    Backwards-compatible wrapper for previous API.
    """
    return generate_lessons(category, n)
