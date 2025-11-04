import json
import os

def load_lessons(path="generated_lessons.json"):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Lesson file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
