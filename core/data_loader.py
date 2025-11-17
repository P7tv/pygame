import json
import os
from pathlib import Path
from typing import Iterable, List, Sequence

DEFAULT_SOURCES: List[str] = [
    os.path.join("data", "generated_lessons.json"),
    os.path.join("data", "lessons_default.json"),
]


def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _unique_paths(paths: Iterable[str | None]) -> List[str]:
    seen = set()
    result: List[str] = []
    for p in paths:
        if not p:
            continue
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


def category_path(category_key: str) -> str:
    return os.path.join("data", f"generated_lessons_{category_key}.json")


def load_lessons(category_key: str | None = None, preferred: str | None = None):
    """
    Load lessons from the preferred source (LLM output if available) and
    gracefully fall back to the built-in defaults.
    """
    sources = _unique_paths(
        [
            preferred,
            category_path(category_key) if category_key else None,
            *DEFAULT_SOURCES,
        ]
    )
    for src in sources:
        if os.path.exists(src):
            try:
                data = _read_json(src)
            except json.JSONDecodeError as exc:
                print(f"[LLM] Invalid lesson JSON '{src}': {exc}")
                continue
            if isinstance(data, list) and data:
                if src != sources[-1]:
                    print(f"[LLM] Loaded lessons from '{src}'")
                return data, src
    raise FileNotFoundError("No valid lesson data found in any source")


def save_lessons(path: str, lessons: Sequence[dict]):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(lessons), f, ensure_ascii=False, indent=2)
