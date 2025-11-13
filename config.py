WIDTH, HEIGHT = 1900, 1080
FPS = 60
FONT_PATH = "assets/fonts/ThaiSansNeue-Black.ttf"

# Colors
WHITE = (255, 255, 255)
GRAY = (245, 247, 250)
GREEN = (88, 204, 2)
BLUE = (28, 176, 246)
RED = (239, 68, 68)
YELLOW = (251, 191, 36)
BLACK = (0, 0, 0)
ORANGE = (251, 191, 36)
PINK = (255, 99, 132)

# Gameplay
LESSON_COUNT = 8

# ASR Config
SAMPLE_RATE = 16000
CHANNELS = 1
MAX_SPEAK_SECONDS = 5
ASR_THRESHOLD_OK = 85
ASR_THRESHOLD_PARTIAL = 65

# Dialect labels
DIALECTS = ["central", "northern", "isan", "southern"]
DIALECT_LABELS = {
    "central": "ภาคกลาง",
    "northern": "ภาคเหนือ",
    "isan": "อีสาน",
    "southern": "ภาคใต้"
}

# Lesson categories
CONTENT_CATEGORIES = [
    {"key": "greetings", "label": "คำทักทายและมารยาทพื้นฐาน"},
    {"key": "pronouns", "label": "สรรพนามส่วนตัว"},
    {"key": "directions", "label": "คำบ่งชี้สถานที่และทิศทาง"},
    {"key": "questions", "label": "คำถามพื้นฐาน (5W1H)"},
    {"key": "feelings", "label": "คำแสดงความรู้สึก/ความเห็น"},
    {"key": "daily", "label": "คำเรียกกลุ่มคำในชีวิตประจำวัน"},
    {"key": "particles", "label": "คำอุทานและคำลงท้าย"},
]
DEFAULT_CATEGORY_KEY = CONTENT_CATEGORIES[0]["key"]

# Challenge mode
CHALLENGE_LEVELS = {
    "easy": {
        "label": "ง่าย",
        "rounds": 4,
        "category_mix": 2,
        "description": "โจทย์สั้น ปน 2 หมวดหมู่",
    },
    "medium": {
        "label": "กลาง",
        "rounds": 6,
        "category_mix": 3,
        "description": "เพิ่มความยากและหมวดหมู่หลากหลาย",
    },
    "hard": {
        "label": "ยาก",
        "rounds": 8,
        "category_mix": 4,
        "description": "โจทย์ยาว + ผสมหมวดแทบทั้งหมด",
    },
}
DEFAULT_CHALLENGE_LEVEL = "easy"
