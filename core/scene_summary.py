import pygame
from core.ui import Button
from config import *

class SummaryScene:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.font = pygame.font.Font(FONT_PATH, 32)

    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return "EXIT"
                if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN: return "MENU"

            self.screen.fill(WHITE)
            msg = self.font.render("สรุปผล: เยี่ยมมาก! ✨", True, GREEN)
            self.screen.blit(msg, msg.get_rect(center=(WIDTH//2, HEIGHT//2)))
            pygame.display.flip()
