from openai import OpenAI
import json

client = OpenAI()

def generate(topic, n=5):
    prompt = f"สร้างบทเรียนสำเนียงไทย {n} บท เช่น 'ผลไม้', 'สัตว์', 'คำทักทาย'"
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )
    text = res.choices[0].message.content
    data = [{"prompt": t.strip(), "targets":{"central":[t.strip()]}} for t in text.split("\n") if t.strip()]
    with open("data/generated_lessons.json","w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
    return data
