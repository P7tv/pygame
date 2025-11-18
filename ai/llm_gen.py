import json
import os
import re
import textwrap
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Sequence

import google.generativeai as genai  # type: ignore

from config import CONTENT_CATEGORIES, DIALECTS, LESSON_COUNT

DEFAULT_MODEL = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-2.0-flash-lite")

CATEGORY_HINTS = {
    "greetings": [
        "กระจายสถานการณ์ทักทายตอนเช้า/บ่าย/เย็น การถามสารทุกข์ และการกล่าวลา/ขอบคุณ",
        "สอดแทรกมารยาทพื้นฐาน เช่น การขอโทษหรือเชื้อเชิญให้ทำกิจกรรมร่วมกัน",
    ],
    "pronouns": [
        "สร้างบริบทที่ต้องใช้สรรพนามบุคคลที่ 1, 2, 3 ทั้งเอกพจน์และพหูพจน์",
        "แสดงตัวเลือกสรรพนามสุภาพ เท่าเทียม และกันเอง เพื่อเทียบความต่างของแต่ละสำเนียง",
    ],
    "directions": [
        "ให้ผู้เรียนบรรยายเส้นทางที่มีซ้าย/ขวา/ตรงไป/ย้อนกลับ/ใกล้/ไกล และจุดสังเกตสำคัญ",
        "ผูกสถานการณ์กับสถานที่จริง เช่น ตลาด โรงเรียน สถานีขนส่ง หรือถนนหลัก",
    ],
    "questions": [
        "ครบทุกบทเรียนต้องกระจายคำถาม 5W1H (ใคร, อะไร, ที่ไหน, เมื่อไร, ทำไม, อย่างไร) โดยไม่ซ้ำรูปแบบ",
        "ใช้สถานการณ์จริง เช่น ถามเส้นทาง สัมภาษณ์ หรือสอบถามเหตุผล",
    ],
    "feelings": [
        "สลับอารมณ์บวก ลบ และกังวล เช่น ดีใจ ผิดหวัง ตื่นเต้น กลัว หรือเห็นต่าง",
        "ให้ prompt กระตุ้นให้ผู้เรียนอธิบายเหตุผลสั้นๆ ร่วมกับคำแสดงอารมณ์",
    ],
    "daily": [
        "หมุนเวียนกิจวัตรหลัก เช่น รับประทานอาหาร เดินทาง ทำงาน ทำความสะอาด ซื้อของ และพักผ่อน",
        "ให้สถานการณ์ชัดเจน (เช้า/หลังเลิกงาน/ก่อนนอน) เพื่อให้ targets แตกต่างกัน",
    ],
    "particles": [
        "แต่ละโจทย์ควรเน้นคำลงท้ายหรือคำอุทานต่างกัน เพื่อสื่อความสุภาพ เน้นย้ำ หรืออารมณ์สนุก",
        "ยกตัวอย่างบริบทที่ทำให้คำลงท้ายมีความหมาย เช่น ขอร้อง ยืนยัน หรือแซวเล่น",
    ],
}


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
    output: List[dict] = []
    for idx, lesson in enumerate(lessons, start=1):
        prompt = str(lesson.get("prompt", "")).strip()
        if not prompt:
            raise ValueError(f"lesson {idx} missing prompt text")
        raw_targets = lesson.get("targets") or {}
        targets: dict[str, List[str]] = {}
        for d in dialects:
            vals = raw_targets.get(d)
            if not isinstance(vals, list):
                raise ValueError(f"lesson {idx} missing targets for dialect '{d}'")
            cleaned = [str(v).strip() for v in vals if str(v).strip()]
            if len(cleaned) < 2:
                raise ValueError(f"lesson {idx} dialect '{d}' needs >=2 phrases")
            targets[d] = cleaned[:3]
        central_words = targets.get("central")
        if central_words:
            central_set = {word for word in central_words if word}
            for d, words in targets.items():
                if d == "central":
                    continue
                if set(words) == central_set:
                    raise ValueError(
                        f"lesson {idx} dialect '{d}' duplicates central targets"
                    )
        output.append({"prompt": prompt, "targets": targets})
    return output


def generate_lessons(category_key: str, count: int = LESSON_COUNT, dialects: Iterable[str] = DIALECTS) -> List[dict]:
    """
    Generate lesson cards for the selected category using Gemini.
    """
    model = _get_model()
    dialects = list(dialects)
    category_label = _category_label(category_key)
    hint_lines = CATEGORY_HINTS.get(category_key)
    hint_block = ""
    if hint_lines:
        bullet_lines = "\n".join(f"          • {line}" for line in hint_lines)
        hint_block = f"\n        เงื่อนไขเฉพาะหมวดนี้:\n{bullet_lines}\n"
    instructions = textwrap.dedent(
        f"""
        บทบาท: คุณคือหัวหน้าทีมออกแบบบทเรียนสำเนียงไทยสไตล์ Duolingo ที่เน้นความถูกต้องของภาษาถิ่น
        ข้อมูลอินพุต:
          • หมวดหมู่บทเรียน: "{category_label}"
          • สำเนียงที่ต้องครอบคลุม: {", ".join(dialects)}
          • จำนวนบทเรียนที่ต้องผลิต: {count}

        เป้าหมาย: สร้าง JSON array ของบทเรียนที่สมจริง ครบถ้วน และพร้อมใช้งานได้ทันทีในเกมฝึกพูด
        {hint_block}

        กรอบการทำงาน (ให้เหตุผลในใจและแสดงเฉพาะผลลัพธ์ JSON):
          1. วิเคราะห์หมวดหมู่ "{category_label}" แล้วร่างสถานการณ์หรือบทสนทนาที่เป็นกลาง (ไม่ยึดสำเนียงใดสำเนียงหนึ่ง) {count} แบบ โดยไม่มีคำซ้ำ
          2. สำหรับแต่ละสถานการณ์ ให้เขียน prompt ภาษาไทยสั้นๆ ชวนพูด และจัดทำ targets ต่อสำเนียงดังนี้:
             • แต่ละสำเนียงต้องมี 2-3 คำ/วลีที่ผู้เรียนสามารถพูดตามได้ทันที
             • ใช้คำท้องถิ่นจริง หลีกเลี่ยงคำแต่งหรือคำที่ไม่ตรงบริบทหมวดหมู่ และหลีกเลี่ยงการซ้ำคำกับสำเนียงอื่น
             • Prompt ต้องเล่าเหตุการณ์เป็นกลาง ใช้ได้กับทุกภาค (ห้ามใช้ประโยคอย่าง "แบบคนภาคกลาง" หรือ "แบบคนเหนือ") แล้วปล่อยให้ targets แสดงความต่างของแต่ละสำเนียง
             • ห้ามใส่คำแปลภาษาอังกฤษหรือคำอธิบายยาว
          3. ตรวจสอบก่อนส่งว่า
             • มีครบ {count} บทเรียน
             • ทุก dialect key ปรากฏในทุกบทเรียน และรายการคำของแต่ละ dialect ไม่ซ้ำกับ dialect อื่น
             • คำตอบไม่มั่ว, ไม่ซ้ำ prompt, และสอดคล้องกับสถานการณ์

        รูปแบบผลลัพธ์: ส่ง JSON array เท่านั้น โดยใช้โครงสร้าง:
        [
          {{
            "prompt": "...",
            "targets": {{
              "central": ["...", "..."],
              "northern": ["..."],
              "isan": ["..."],
              "southern": ["..."]
            }}
          }}
        ]
        ห้ามตอบคำอื่นนอกเหนือ JSON
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
    try:
        cleaned = _ensure_dialects(data, dialects)
    except ValueError as exc:
        raise RuntimeError(f"Gemini returned invalid lesson data: {exc}") from exc
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
