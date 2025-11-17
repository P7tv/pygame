import pygame
import math
import time
from core.ui import Button, PRIMARY, SECONDARY, ACCENT, LIGHT_TEXT, DARK_BG, WHITE, BLACK
from config import *


class SummaryScene:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen

        # Fonts
        self.title_font = pygame.font.Font(FONT_PATH, 72)
        self.header_font = pygame.font.Font(FONT_PATH, 48)
        self.label_font = pygame.font.Font(FONT_PATH, 36)
        self.font = pygame.font.Font(FONT_PATH, 28)

        self.xp = self.game.state.get("xp", 0)
        self.streak = self.game.state.get("streak", 0)
        self.hearts = self.game.state.get("hearts", 3)
        self.start_time = time.time()

    def run(self):
        back_btn = Button(
            pygame.Rect(WIDTH // 2 - 150, HEIGHT - 150, 300, 80),
            "← กลับไปเมนู",
            SECONDARY,
            WHITE,
            radius=40
        )

        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return "EXIT"
                if e.type == pygame.VIDEORESIZE:
                    self.game.handle_resize(e)
                if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                        return "MENU"

                    pointer = self.game.logical_pos(e.pos) if hasattr(e, "pos") else None
                    if pointer and back_btn.collide(pointer):
                        return "MENU"
                    elif e.type == pygame.KEYDOWN:
                        return "MENU"

            self._draw(back_btn)
            self.game.present()

    def _draw(self, back_btn):
        """Draw summary screen with celebration"""
        # Background
        self.screen.fill((240, 250, 255))

        # Header bar
        pygame.draw.rect(self.screen, DARK_BG, (0, 0, WIDTH, 120))
        pygame.draw.line(self.screen, (220, 220, 220), (0, 119), (WIDTH, 119), 1)

        title = self.title_font.render("🎉 บทเรียนเสร็จสิ้น!", True, WHITE)
        self.screen.blit(title, (50, 25))

        # Main content card
        card_rect = pygame.Rect(200, 200, WIDTH - 400, 600)
        pygame.draw.rect(self.screen, WHITE, card_rect, border_radius=30)
        pygame.draw.rect(self.screen, (220, 220, 220), card_rect, 2, border_radius=30)

        # Performance message
        if self.hearts > 0:
            msg = "ยอดเยี่ยม! ✨ คุณทำได้ดีมาก"
            msg_color = PRIMARY
        else:
            msg = "ลองใหม่ ซ้ำที่เดิมอีกครั้ง 💪"
            msg_color = (255, 140, 0)

        # Scale font down if message is too wide
        max_msg_width = card_rect.width - 80
        msg_txt = self.header_font.render(msg, True, msg_color)
        
        if msg_txt.get_width() > max_msg_width:
            current_size = 48
            while current_size > 24 and msg_txt.get_width() > max_msg_width:
                current_size -= 2
                scaled_font = pygame.font.Font(FONT_PATH, current_size)
                msg_txt = scaled_font.render(msg, True, msg_color)
        
        self.screen.blit(msg_txt, (card_rect.x + 40, card_rect.y + 50))

        # Stats display
        stats_y = card_rect.y + 180

        # XP earned
        xp_bg = pygame.Rect(card_rect.x + 40, stats_y, (card_rect.width - 80) // 2 - 10, 140)
        pygame.draw.rect(self.screen, (240, 250, 255), xp_bg, border_radius=20)
        pygame.draw.rect(self.screen, ACCENT, xp_bg, 3, border_radius=20)

        xp_label = self.label_font.render("XP ที่ได้", True, LIGHT_TEXT)
        self.screen.blit(xp_label, (xp_bg.x + 20, xp_bg.y + 10))

        xp_value = self.title_font.render(f"+{self.xp}", True, ACCENT)
        self.screen.blit(xp_value, (xp_bg.x + 20, xp_bg.y + 60))

        # Streak counter
        streak_bg = pygame.Rect(card_rect.x + (card_rect.width // 2) + 10, stats_y, (card_rect.width - 80) // 2 - 10, 140)
        pygame.draw.rect(self.screen, (255, 245, 240), streak_bg, border_radius=20)
        pygame.draw.rect(self.screen, (255, 140, 0), streak_bg, 3, border_radius=20)

        streak_label = self.label_font.render("🔥 Streak", True, LIGHT_TEXT)
        self.screen.blit(streak_label, (streak_bg.x + 20, streak_bg.y + 10))

        streak_value = self.title_font.render(f"{self.streak}", True, (255, 100, 0))
        self.screen.blit(streak_value, (streak_bg.x + 20, streak_bg.y + 60))

        # Hearts remaining
        hearts_y = stats_y + 170
        hearts_label = self.label_font.render(f"❤️ หัวใจเหลือ: {self.hearts}/3", True, LIGHT_TEXT)
        self.screen.blit(hearts_label, (card_rect.x + 40, hearts_y))

        # Motivational message
        if self.streak > 5:
            motiv = "👏 ยังไงก็เก่งมากแล้ว! ต่อเนื่องไปเรื่อย ๆ นะ!"
        elif self.streak > 0:
            motiv = "💪 ทำได้ดี เล่นอีกครั้งเพื่อสร้าง streak!"
        else:
            motiv = "🎯 เริ่มต้นใหม่ครับ ลองบทเรียนอื่น ๆ ดูนะ"

        # Scale font down if message is too wide
        max_motiv_width = card_rect.width - 80
        motiv_txt = self.font.render(motiv, True, LIGHT_TEXT)
        
        if motiv_txt.get_width() > max_motiv_width:
            current_size = 28
            while current_size > 16 and motiv_txt.get_width() > max_motiv_width:
                current_size -= 2
                scaled_font = pygame.font.Font(FONT_PATH, current_size)
                motiv_txt = scaled_font.render(motiv, True, LIGHT_TEXT)
        
        self.screen.blit(motiv_txt, (card_rect.x + 40, hearts_y + 60))

        # Back button
        mouse_pos = self.game.mouse_pos()
        back_btn.draw(self.screen, self.label_font, hovered=back_btn.collide(mouse_pos))
