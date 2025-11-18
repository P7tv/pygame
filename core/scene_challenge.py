import random
import pygame
from config import *
from core.ui import Button, Card, PRIMARY, SECONDARY, ACCENT, LIGHT_TEXT, DARK_BG, WHITE, BORDER_COLOR, render_text_wrapped
from core.sound_manager import SoundManager


class ChallengeScene:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen

        # Fonts
        self.title_font = pygame.font.Font(FONT_PATH, 64)
        self.header_font = pygame.font.Font(FONT_PATH, 52)
        self.label_font = pygame.font.Font(FONT_PATH, 32)
        self.desc_font = pygame.font.Font(FONT_PATH, 28)
        self.card_title_font = pygame.font.Font(FONT_PATH, 40)

        self.levels = CHALLENGE_LEVEL_ORDER
        self._create_buttons()

    def _create_buttons(self):
        """Create challenge level buttons"""
        self.level_cards = []

        # Card dimensions
        card_width = 360
        card_height = 240
        gap = 40
        total_width = card_width * 3 + gap * 2
        start_x = (WIDTH - total_width) // 2
        start_y = 320

        colors = [PRIMARY, SECONDARY, ACCENT]

        for i, (level, color) in enumerate(zip(self.levels, colors)):
            x = start_x + i * (card_width + gap)
            card = Card("", x, start_y, card_width, card_height)
            self.level_cards.append((level, card, color, CHALLENGE_LEVELS[level]["label"]))

    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return "EXIT"
                if e.type == pygame.VIDEORESIZE:
                    self.game.handle_resize(e)
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    return "MENU"

                pointer = self.game.logical_pos(e.pos) if hasattr(e, "pos") else None
                if e.type == pygame.MOUSEBUTTONDOWN and pointer:
                    sound_mgr = SoundManager()
                    for level, card, _, _ in self.level_cards:
                        if card.collide(pointer):
                            if not self._is_unlocked(level):
                                sound_mgr.play_bad()
                                continue
                            sound_mgr.play_ok()
                            return self._start_challenge(level)

            self._draw()
            self.game.present()

    def _start_challenge(self, level):
        """Start challenge mode with given level"""
        cfg = CHALLENGE_LEVELS[level]
        self.game.state.update({
            "mode": "challenge",
            "challenge_level": level,
            "challenge_mix": [c["key"] for c in random.sample(CONTENT_CATEGORIES, cfg["category_mix"])]
        })
        return "LESSON"

    def _draw(self):
        """Draw challenge selection screen"""
        # Background
        self.screen.fill(WHITE)

        # Header
        pygame.draw.rect(self.screen, DARK_BG, (0, 0, WIDTH, 150))
        pygame.draw.line(self.screen, (220, 220, 220), (0, 149), (WIDTH, 149), 1)

        title = self.title_font.render("⚡ โหมดชาเลนจ์", True, GREEN)
        self.screen.blit(title, (50, 35))

        # Subtitle
        subtitle = self.header_font.render("เลือกระดับความยาก", True, LIGHT_TEXT)
        self.screen.blit(subtitle, (50, 200))

        # Level cards
        mouse_pos = self.game.mouse_pos()
        for level, card, color, title_text in self.level_cards:
            cfg = CHALLENGE_LEVELS[level]
            locked = not self._is_unlocked(level)
            card.draw(self.screen, self.label_font, selected=not locked)

            card_rect = card.rect
            # draw title near top of card
            title_color = color if not locked else (160, 160, 160)
            title = self.card_title_font.render(title_text, True, title_color)
            title_rect = title.get_rect()
            title_rect.centerx = card_rect.centerx
            title_rect.y = card_rect.y + 24
            self.screen.blit(title, title_rect)
            desc_text = cfg["description"]
            max_desc_width = card_rect.width - 40

            # Render description with wrapping to avoid overflow
            desc_color = LIGHT_TEXT if not locked else (140, 140, 140)
            desc_lines = render_text_wrapped(self.desc_font, desc_text, desc_color, max_desc_width)
            text_y = title_rect.bottom + 20
            if locked:
                lock_msg = "🔒 ผ่านระดับก่อนหน้าก่อน"
                lock_lines = render_text_wrapped(self.desc_font, lock_msg, desc_color, max_desc_width)
                for line in lock_lines[:2]:
                    self.screen.blit(line, (card_rect.x + 20, text_y))
                    text_y += line.get_height() + 6
                continue
            for line in desc_lines[:2]:  # limit to 2 lines to keep layout tidy
                self.screen.blit(line, (card_rect.x + 20, text_y))
                text_y += line.get_height() + 6

            rounds_text = f"{cfg['rounds']} ข้อ • {cfg['category_mix']} หมวด"
            rounds = self.label_font.render(rounds_text, True, LIGHT_TEXT)
            # shrink rounds line if needed
            if rounds.get_width() > max_desc_width:
                current_size = self.label_font.get_height()
                while current_size > 18 and rounds.get_width() > max_desc_width:
                    current_size -= 2
                    scaled_font = pygame.font.Font(FONT_PATH, current_size)
                    rounds = scaled_font.render(rounds_text, True, LIGHT_TEXT)
            self.screen.blit(rounds, (card_rect.x + 20, text_y + 10))

        # Back button
        back_btn = Button(
            pygame.Rect(60, HEIGHT - 180, 280, 90),
            "← กลับ",
            SECONDARY,
            WHITE,
            radius=28
        )
        back_btn.draw(self.screen, self.label_font, hovered=back_btn.collide(mouse_pos))

    def _is_unlocked(self, level: str) -> bool:
        unlocked = self.game.state.setdefault("challenge_unlocked", DEFAULT_CHALLENGE_UNLOCK.copy())
        return unlocked.get(level, False)
