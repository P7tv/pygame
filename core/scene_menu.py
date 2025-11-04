import pygame
from config import *
from core.ui import Button

class MenuScene:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.font = pygame.font.Font(FONT_PATH, 36)
        self.buttons = {
            "lesson": Button(pygame.Rect(240, 300, 320, 60), "เริ่มบทเรียน ▶", GREEN, WHITE),
            "free": Button(pygame.Rect(240, 380, 320, 60), "โหมดพูดอิสระ 🎤", BLUE, WHITE)
        }

    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return "EXIT"
                if e.type == pygame.MOUSEBUTTONDOWN:
                    if self.buttons["lesson"].rect.collidepoint(e.pos): return "LESSON"
                    if self.buttons["free"].rect.collidepoint(e.pos): return "FREE"

            self.screen.fill(WHITE)
            title = self.font.render("ภาษาถิ่นไทย", True, BLACK)
            self.screen.blit(title, title.get_rect(center=(WIDTH//2, 150)))
            for b in self.buttons.values():
                b.draw(self.screen, self.font, hovered=b.rect.collidepoint(pygame.mouse.get_pos()))
            pygame.display.flip()
