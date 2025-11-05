import pygame, sys
from config import *

class Game:
    def __init__(self, scenes):
        pygame.init()
        pygame.display.set_caption("🦉 Duolingo Thai Dialects")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.current_scene = None
        self.scene_map = scenes
        self.state = {
            "xp": 0,
            "streak": 0,
            "best_streak": 0,
            "hearts": 3,
            "dialect": DIALECTS[0],
            "category": DEFAULT_CATEGORY_KEY,
        }
        self.dialect = self.state["dialect"]
        self.category = self.state["category"]
        self.switch_scene("MENU")

    def switch_scene(self, name):
        scene_class = self.scene_map.get(name)
        if scene_class:
            self.current_scene = scene_class(self)
            self.current_scene_name = name

    def run(self):
        while self.running:
            result = self.current_scene.run()
            if result in self.scene_map:
                self.switch_scene(result)
            elif result == "EXIT":
                self.running = False
        pygame.quit()
        sys.exit()
