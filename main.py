"""จุดเริ่มโปรแกรม: ประกอบ mapping ของทุก scene แล้วส่งให้ Game"""

from core.game import Game
from core.scene_menu import MenuScene
from core.scene_lesson import LessonScene
from core.scene_free import FreeSpeakScene
from core.scene_summary import SummaryScene
from core.scene_challenge import ChallengeScene

from config import *


if __name__ == "__main__":
    # รวบรวมชื่อ scene -> คลาสไว้ใช้ในการสลับฉากใน game loop
    scenes = {
        "MENU": MenuScene,
        "LESSON": LessonScene,
        "FREE": FreeSpeakScene,
        "CHALLENGE": ChallengeScene,
        "SUMMARY": SummaryScene
    }
    # สร้างอินสแตนซ์ Game พร้อม map แล้วเริ่มรันลูปหลัก
    game = Game(scenes)
    game.run()
