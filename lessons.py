import json, os
from typing import List, Dict
from config import DIALECTS

DEFAULT_LESSONS = [
    {"prompt":"พูดคำว่า 'อร่อย' เป็นสำเนียงของคุณ",
     "targets":{"central":["อร่อย"],"northern":["ลำ","จ๊าดลำ"],"isan":["แซบ","แซบหลาย"],"southern":["หรอย","หรอยแรง"]}},
    {"prompt":"พูดคำว่า 'กินข้าว' เป็นสำเนียงของคุณ",
     "targets":{"central":["กินข้าว"],"northern":["กิ๋นข้าว"],"isan":["กินเข่า","กินข้าว"],"southern":["กินข้าว"]}},
    {"prompt":"พูดว่า 'ไปโรงเรียน' เป็นสำเนียงของคุณ",
     "targets":{"central":["ไปโรงเรียน"],"northern":["ไปตี้โฮงเฮียน"],"isan":["ไปโรงเฮียน"],"southern":["ไปโรงเรียน"]}},
    {"prompt":"พูดว่า 'สวัสดี'",
     "targets":{"central":["สวัสดี"],"northern":["สวัสดีเจ้า"],"isan":["สวัสดีเด้อ"],"southern":["สวัสดีแหลง"]}},
]

def validate(data: list) -> list:
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if "prompt" not in item or "targets" not in item:
            continue
        tg = dict(item["targets"]) if isinstance(item["targets"], dict) else {}
        # ensure all dialects exist
        for d in DIALECTS:
            tg.setdefault(d, tg.get("central", []))
        out.append({"prompt": str(item["prompt"]), "targets": tg})
    return out

def load_json(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    v = validate(data)
    return v if v else DEFAULT_LESSONS

def save_json(path: str, lessons: list):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(lessons, f, ensure_ascii=False, indent=2)