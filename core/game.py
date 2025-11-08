import pygame, sys
from config import *

class Game:
    def __init__(self, scenes):
        pygame.init()
        pygame.display.set_caption("🦉 Duolingo Thai Dialects")
        self.base_size = (WIDTH, HEIGHT)
        self.display = pygame.display.set_mode(self.base_size, pygame.RESIZABLE)
        self.canvas = pygame.Surface(self.base_size, pygame.SRCALPHA).convert_alpha()
        self.screen = self.canvas  # compatibility for existing scenes
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

    def _scale_factor(self):
        win_w, win_h = self.display.get_size()
        base_w, base_h = self.base_size
        scale_x = base_w / win_w if win_w else 1
        scale_y = base_h / win_h if win_h else 1
        return scale_x, scale_y

    def logical_pos(self, pos):
        """Convert window coordinates to the base canvas coordinates."""
        sx, sy = self._scale_factor()
        return (int(pos[0] * sx), int(pos[1] * sy))

    def mouse_pos(self):
        """Return current mouse position mapped to canvas coordinates."""
        return self.logical_pos(pygame.mouse.get_pos())

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

    def handle_resize(self, event):
        new_size = (max(event.w, 640), max(event.h, 480))
        self.display = pygame.display.set_mode(new_size, pygame.RESIZABLE)

    def present(self):
        window_size = self.display.get_size()
        if window_size == self.base_size:
            self.display.blit(self.canvas, (0, 0))
        else:
            scaled = pygame.transform.smoothscale(self.canvas, window_size)
            self.display.blit(scaled, (0, 0))
        pygame.display.flip()
