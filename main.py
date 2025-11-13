from core.game import Game
from core.scene_menu import MenuScene
from core.scene_lesson import LessonScene
from core.scene_free import FreeSpeakScene
from core.scene_summary import SummaryScene
from core.scene_challenge import ChallengeScene

from config import *

if __name__ == "__main__":
    scenes = {
        "MENU": MenuScene,
        "LESSON": LessonScene,
        "FREE": FreeSpeakScene,
        "CHALLENGE": ChallengeScene,
        "SUMMARY": SummaryScene
    }
    game = Game(scenes)
    game.run()
