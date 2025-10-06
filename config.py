# UI & Game
WIDTH, HEIGHT, FPS = 1280, 720, 60
BG, FG = (40, 40, 60), (230, 230, 230)  # สีพื้นหลังและสีตัวอักษร
ACCENT, WARN, MUTED, CARD, PROGRESS = (100,220,140), (255,120,120), (130,130,150), (50,50,70), (140,180,255)  # สีเน้นต่างๆ

SAVE_PATH = "save.json"
# ใส่ฟอนต์ไทยจะสวยกว่า (เช่น NotoSansThai). ถ้าไม่มีก็ปล่อย None
FONT_PATH = None # "assets/fonts/NotoSansThai-Regular.ttf"

# ASR (Whisper)
ASR_ENABLED = True
ASR_MODEL_SIZE = "small" # "tiny"/"base"/"small"/"medium"
ASR_LANGUAGE = "th"
ASR_THRESHOLD_OK = 85
ASR_THRESHOLD_PARTIAL = 70
SAMPLE_RATE = 16000
CHANNELS = 1
MAX_SPEAK_SECONDS = 4.0

# Dialects
DIALECTS = ["central","northern","isan","southern"]
DIALECT_LABELS = {
"central":"กลาง",
"northern":"เหนือ (คำเมือง)",
"isan":"อีสาน",
"southern":"ใต้",
}
NORMALIZE_MAP = {
"northern": {
"กิ๋น":"กิน", "จ๊าด":"มาก", "ลำ":"อร่อย", "ปิ๊ก":"กลับ", "ตี้":"ที่", "ยะ":"ทำ", "ละอ่อน":"เด็ก",
},
"isan": {
"แซบ":"อร่อย", "เด้อ":"", "จัก":"สัก", "อยู่บ่":"อยู่ไหม", "บ่":"ไม่", "หลาย":"มาก", "เข่า":"ข้าว",
},
"southern": {
"หรอย":"อร่อย", "นิ":"นี่", "แล":"ดู", "พรือ":"อย่างไร", "หม้าย":"ไหม", "หล่าว":"แล้ว",
},
}