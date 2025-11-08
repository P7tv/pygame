import pygame
from dataclasses import dataclass
from config import *

ORANGE = (251, 191, 36)
PINK = (255, 99, 132)

@dataclass
class Button:
    rect: pygame.Rect
    label: str
    bg: tuple
    fg: tuple
    radius: int = 20
    shadow: bool = True

    def draw(self, surf, font, hovered=False):
        color = tuple(min(255, int(c * (1.1 if hovered else 1))) for c in self.bg)
        if self.shadow:
            shadow_rect = self.rect.move(3, 3)
            pygame.draw.rect(surf, (200, 200, 200), shadow_rect, border_radius=self.radius)
        pygame.draw.rect(surf, color, self.rect, border_radius=self.radius)
        txt = font.render(self.label, True, self.fg)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

class TextField:
    def __init__(self, rect, font, placeholder=""):
        self.rect = rect
        self.font = font
        self.text = ""
        self.placeholder = placeholder
        self.focus = False

    def handle(self, event, pointer_pos=None):
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = pointer_pos if pointer_pos is not None else getattr(event, "pos", None)
            if pos is not None:
                self.focus = self.rect.collidepoint(pos)
        elif self.focus and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                return "submit"
            elif event.unicode:
                self.text += event.unicode
        return None

    def draw(self, surf):
        pygame.draw.rect(surf, WHITE if self.focus else GRAY, self.rect, border_radius=12)
        text = self.text or self.placeholder
        color = BLACK if self.text else (160, 174, 192)
        surf.blit(self.font.render(text, True, color), (self.rect.x+10, self.rect.y+10))

def draw_status(surf, font, feedback=None, score=None, progress=None):
    """Draws status bar at the top of the screen."""
    status_text = ""
    if feedback:
        kind, val, text = feedback
        if kind == "ok":
            status_text += "✅ ถูกต้อง "
        elif kind == "partial":
            status_text += "⚠️ ใกล้เคียง "
        else:
            status_text += "❌ ลองใหม่ "
        status_text += f"({val}) | \"{text}\""
    if score is not None:
        status_text += f"   คะแนน: {score}"
    if progress is not None:
        status_text += f"   ข้อที่ {progress[0]}/{progress[1]}"
    if status_text:
        bar_rect = pygame.Rect(0, 0, WIDTH, 50)
        pygame.draw.rect(surf, GRAY, bar_rect)
        txt = font.render(status_text, True, BLACK)
        surf.blit(txt, (20, 10))

class Chip:
    def __init__(self, text, bg, fg):
        self.text = text
        self.bg = bg
        self.fg = fg

    def draw(self, surf, font, x, y):
        txt = font.render(self.text, True, self.fg)
        rect = pygame.Rect(x, y, txt.get_width()+32, txt.get_height()+16)
        pygame.draw.rect(surf, self.bg, rect, border_radius=16)
        surf.blit(txt, (rect.x+16, rect.y+8))

class ProgressBar:
    def __init__(self, value, total):
        self.value = value
        self.total = total

    def draw(self, surf, x, y, w, h):
        pygame.draw.rect(surf, GRAY, (x, y, w, h), border_radius=h//2)
        if self.total > 0:
            fill = int(w * self.value / self.total)
            pygame.draw.rect(surf, BLUE, (x, y, fill, h), border_radius=h//2)
        pygame.draw.rect(surf, BLACK, (x, y, w, h), 2, border_radius=h//2)

class HeaderUI:
    def __init__(self, xp, streak, hearts, dialect, progress, total):
        self.xp = xp
        self.streak = streak
        self.hearts = hearts
        self.dialect = dialect
        self.progress = progress
        self.total = total

    def update(self, xp, streak, hearts, dialect, progress, total):
        self.xp = xp
        self.streak = streak
        self.hearts = hearts
        self.dialect = dialect
        self.progress = progress
        self.total = total

    def draw(self, surf):
        font = pygame.font.Font(FONT_PATH, 22)
        # XP
        pygame.draw.circle(surf, YELLOW, (40, 36), 18)
        xp_txt = font.render(str(self.xp), True, BLACK)
        surf.blit(xp_txt, (28, 26))
        # Streak
        if self.streak > 0:
            fire = font.render("🔥", True, (255, 120, 0))
            surf.blit(fire, (80, 20))
            streak_txt = font.render(str(self.streak), True, BLACK)
            surf.blit(streak_txt, (110, 26))
        # Hearts
        for i in range(3):
            color = RED if i < self.hearts else GRAY
            heart = font.render("❤️", True, color)
            surf.blit(heart, (160+i*32, 22))
        # Dialect tag
        tag_map = {
            "central": (GREEN, "ภาคกลาง"),
            "northern": (BLUE, "เหนือ"),
            "isan": (ORANGE, "อีสาน"),
            "southern": (PINK, "ใต้")
        }
        tag_color, tag_label = tag_map.get(self.dialect, (GRAY, ""))
        tag_rect = pygame.Rect(270, 22, 80, 28)
        pygame.draw.rect(surf, tag_color, tag_rect, border_radius=14)
        tag_txt = font.render(tag_label, True, WHITE)
        surf.blit(tag_txt, (278, 26))
        surf.blit(tag_txt, (tag_rect.x+12, tag_rect.y+4))
        # Progress bar
        ProgressBar(self.progress, self.total).draw(surf, 370, 28, 220, 16)
