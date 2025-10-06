import json, re, textwrap
from openai import OpenAI
from config import DIALECTS

# ---- ตั้งค่าตรงนี้ ----
API_KEY   = "sk-VL6FVfEvqs8uY4fo5CfiKqnG6Wy2Kf2jwrXC3HQjGEPemPmR"
BASE_URL  = "https://api.opentyphoon.ai/v1"
MODEL     = "typhoon-v2.1-12b-instruct"
# -----------------------

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def _extract_json(s: str) -> str:
    m = re.search(r"\[[\s\S]*\]", s)
    return m.group(0) if m else s

def generate(topic: str, n: int = 8):
    # เพิ่มความซับซ้อนของ prompt โดยเน้นการใช้สำนวนภาษาถิ่นที่หลากหลาย
    system = textwrap.dedent(f"""
    คุณคือผู้ช่วยสร้างบทเรียนภาษาไทยถิ่นสำหรับเกม โดยเน้นโหมด 'พูดล้วน' ที่ท้าทายและสร้างสรรค์
    คืนค่าเป็น JSON เท่านั้น (ห้ามมีคำอธิบายหรือโค้ดบล็อกใดๆ ทั้งสิ้น)
    ตัวอย่าง:
    [
      {{
        "prompt": "จงใช้สำนวนภาษาถิ่นของคุณอธิบายว่า 'การได้กินอาหารอร่อยหลังจากทำงานเหนื่อยมาทั้งวัน' เป็นอย่างไร",
        "targets": {{
          "central": ["กินของอร่อยหลังเลิกงาน"],
          "northern": ["กิ๋นข้าวลำหลังเลิกงาน"],
          "isan": ["กินเข่าแซบๆ หลังเลิกงาน"],
          "southern": ["กินข้าวหรอยๆ หลังเลิกงาน"]
        }}
      }}
    ]
    คำแนะนำ:
    - สร้างบทเรียนที่เน้นการใช้สำนวนภาษาถิ่นที่หลากหลายและน่าสนใจ
    - กระตุ้นให้ผู้เล่นคิดและใช้ภาษาถิ่นอย่างสร้างสรรค์
    - โจทย์ควรมีความท้าทายแต่ไม่ยากเกินไป
    - อย่าลืมว่าต้องคืนค่าเป็น JSON เท่านั้น
    สร้าง {n} ข้อ โดยมีหัวข้อหลักคือ '{topic}'
    """)
    user = f"สร้างบทเรียน {n} ข้อ สำหรับหัวข้อ: {topic}"

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        temperature=0.2, max_tokens=2048
    )
    raw = resp.choices[0].message.content.strip()
    data = json.loads(_extract_json(raw))

    # เพิ่ม dialect ที่ขาดให้ครบ
    for it in data:
        tg = it.setdefault("targets", {})
        for d in DIALECTS:
            tg.setdefault(d, tg.get("central", []))
    return data
