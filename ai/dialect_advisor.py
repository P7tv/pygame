from openai import OpenAI

client = OpenAI()

def suggest_feedback(text, dialect):
    prompt = f"ผู้เรียนพูดว่า '{text}' ในสำเนียง {dialect} ช่วยแนะนำคำพูดที่ถูกต้องและให้คำแนะนำการออกเสียง"
    res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
    return res.choices[0].message.content
