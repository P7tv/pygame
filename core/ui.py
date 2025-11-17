import pygame
from dataclasses import dataclass
from config import *

# === พาเลตต์สีโทน Duolingo ===
PRIMARY = (58, 150, 94)      # เขียว
SECONDARY = (255, 165, 0)    # ส้ม
ACCENT = (50, 120, 255)      # น้ำเงิน
DARK_BG = (248, 249, 250)
LIGHT_TEXT = (51, 51, 51)
BORDER_COLOR = (220, 220, 220)


# คอมโพเนนต์ปุ่มแบบมีเงา ใช้ร่วมกันทุก scene
@dataclass
class Button:
    rect: pygame.Rect
    label: str
    bg: tuple
    fg: tuple
    radius: int = 12
    shadow: bool = True
    border_width: int = 0

    def draw(self, surf, font, hovered=False):
        """วาดปุ่มพร้อมจัดการ hover/shadow"""
        color = tuple(min(255, int(c * (1.12 if hovered else 1))) for c in self.bg)
        if self.shadow and not hovered:
            shadow_rect = self.rect.move(0, 3)
            pygame.draw.rect(surf, (200, 200, 200, 100), shadow_rect, border_radius=self.radius)
        pygame.draw.rect(surf, color, self.rect, border_radius=self.radius)
        if self.border_width > 0:
            pygame.draw.rect(surf, BORDER_COLOR, self.rect, self.border_width, border_radius=self.radius)
        txt = font.render(self.label, True, self.fg)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def collide(self, pos):
        """ตรวจว่าจุดที่ให้มาตกอยู่ในพื้นที่ปุ่มหรือไม่"""
        return self.rect.collidepoint(pos)


class TextField:
    def __init__(self, rect, font, placeholder=""):
        """กล่องข้อความง่าย ๆ สำหรับรับอินพุตจากคีย์บอร์ด"""
        self.rect = rect
        self.font = font
        self.text = ""
        self.placeholder = placeholder
        self.focus = False

    def handle(self, event, pointer_pos=None):
        """ประมวลผล event คลิก/คีย์ แล้วปรับ focus หรือข้อความ"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = pointer_pos if pointer_pos is not None else getattr(event, "pos", None)
            self.focus = self.rect.collidepoint(pos) if pos else False
        elif self.focus and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                return "submit"
            elif event.unicode:
                self.text += event.unicode
        return None

    def draw(self, surf):
        """วาดกล่องข้อความและตัวอักษร (หรือ placeholder)"""
        color = WHITE if self.focus else DARK_BG
        pygame.draw.rect(surf, color, self.rect, border_radius=12)
        pygame.draw.rect(surf, ACCENT if self.focus else BORDER_COLOR, self.rect, 2, border_radius=12)
        text = self.text or self.placeholder
        text_color = BLACK if self.text else (160, 160, 160)
        surf.blit(self.font.render(text, True, text_color), (self.rect.x + 16, self.rect.y + 12))


class Chip:
    def __init__(self, text, bg, fg):
        """ชิปเล็ก ๆ ใช้เน้นข้อความ"""
        self.text = text
        self.bg = bg
        self.fg = fg

    def draw(self, surf, font, x, y):
        """วาดชิปที่ตำแหน่งกำหนดแล้วคืน rect สำหรับใช้งานต่อ"""
        txt = font.render(self.text, True, self.fg)
        rect = pygame.Rect(x, y, txt.get_width() + 24, txt.get_height() + 14)
        pygame.draw.rect(surf, self.bg, rect, border_radius=20)
        surf.blit(txt, (rect.x + 12, rect.y + 7))
        return rect


class ProgressBar:
    def __init__(self, value, total):
        """progress bar เรียบง่ายไว้โชว์ความคืบหน้า"""
        self.value = value
        self.total = total

    def draw(self, surf, x, y, w, h):
        """วาดกรอบและสัดส่วนของ progress ตาม value"""
        pygame.draw.rect(surf, BORDER_COLOR, (x, y, w, h), border_radius=h // 2)
        if self.total > 0:
            fill = int(w * self.value / self.total)
            pygame.draw.rect(surf, PRIMARY, (x, y, fill, h), border_radius=h // 2)


class HeaderUI:
    """แถบด้านบนแสดง XP, หัวใจ, และความคืบหน้า"""

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
        # พื้นหลังสีขาวพร้อมเส้นคั่น
        pygame.draw.rect(surf, WHITE, (0, 0, WIDTH, 80))
        pygame.draw.line(surf, BORDER_COLOR, (0, 79), (WIDTH, 79), 1)

        font = pygame.font.Font(FONT_PATH, 24)
        small_font = pygame.font.Font(FONT_PATH, 18)

        # มุมซ้าย: แสดง XP ปัจจุบัน
        xp_badge = pygame.Rect(20, 15, 60, 50)
        pygame.draw.rect(surf, SECONDARY, xp_badge, border_radius=10)
        xp_txt = small_font.render(str(self.xp), True, WHITE)
        surf.blit(xp_txt, (xp_badge.x + 15, xp_badge.y + 8))
        xp_label = pygame.font.Font(FONT_PATH, 12).render("XP", True, WHITE)
        surf.blit(xp_label, (xp_badge.x + 18, xp_badge.y + 28))

        # กลาง: แถบความคืบหน้าบทเรียน
        progress_rect = pygame.Rect(WIDTH // 2 - 150, 30, 300, 20)
        ProgressBar(self.progress, self.total).draw(surf, progress_rect.x, progress_rect.y, progress_rect.w, progress_rect.h)
        progress_txt = small_font.render(f"{self.progress}/{self.total}", True, LIGHT_TEXT)
        surf.blit(progress_txt, (progress_rect.x + progress_rect.w + 15, progress_rect.y - 2))

        # ขวา: จำนวนหัวใจและ streak
        heart_x = WIDTH - 200
        for i in range(3):
            heart_color = RED if i < self.hearts else BORDER_COLOR
            heart = font.render("❤️", True, heart_color)
            surf.blit(heart, (heart_x + i * 40, 20))

        if self.streak > 0:
            fire = font.render("🔥", True, SECONDARY)
            surf.blit(fire, (WIDTH - 80, 20))
            streak_txt = small_font.render(str(self.streak), True, LIGHT_TEXT)
            surf.blit(streak_txt, (WIDTH - 50, 25))


class Card:
    """การ์ดเลือกที่ใช้ในเมนู/ชาเลนจ์สไตล์ Duolingo"""

    def __init__(self, text, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.hovered = False

    def draw(self, surf, font, selected=False):
        """วาดการ์ดพร้อมสถานะ selected"""
        bg = PRIMARY if selected else WHITE
        text_color = WHITE if selected else LIGHT_TEXT
        pygame.draw.rect(surf, bg, self.rect, border_radius=16)
        pygame.draw.rect(surf, PRIMARY if selected else BORDER_COLOR, self.rect, 2 if selected else 1, border_radius=16)
        txt = font.render(self.text, True, text_color)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def collide(self, pos):
        """ตรวจว่าจุดอยู่ภายในการ์ด (ใช้สำหรับคลิก/hover)"""
        return self.rect.collidepoint(pos)


def draw_status(surface, font, text, pos, color=LIGHT_TEXT):
    """helper วาดข้อความสถานะสั้น ๆ บน surface"""
    label = font.render(text, True, color)
    surface.blit(label, pos)
