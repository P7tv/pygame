import random
import pygame
from config import *
from core.ui import Button, Card, PRIMARY, SECONDARY, ACCENT, LIGHT_TEXT, DARK_BG, WHITE
from core.sound_manager import SoundManager


class ChallengeScene:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen

        # Fonts
        self.title_font = pygame.font.Font(FONT_PATH, 64)
        self.header_font = pygame.font.Font(FONT_PATH, 48)
        self.label_font = pygame.font.Font(FONT_PATH, 28)
        self.desc_font = pygame.font.Font(FONT_PATH, 24)

        self.levels = ["easy", "medium", "hard"]
        self._create_buttons()

    def _create_buttons(self):
        """Create challenge level buttons"""
        self.level_cards = []

        # Card dimensions
        card_width = 280
        card_height = 200
        gap = 30
        total_width = card_width * 3 + gap * 2
        start_x = (WIDTH - total_width) // 2
        start_y = 280

        colors = [PRIMARY, SECONDARY, ACCENT]

        for i, (level, color) in enumerate(zip(self.levels, colors)):
            x = start_x + i * (card_width + gap)
            card = Card(CHALLENGE_LEVELS[level]["label"], x, start_y, card_width, card_height)
            self.level_cards.append((level, card, color))

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
                    for level, card, _ in self.level_cards:
                        if card.collide(pointer):
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

        title = self.title_font.render("⚡ โหมดชาเลนจ์", True, WHITE)
        self.screen.blit(title, (50, 35))

        # Subtitle
        subtitle = self.header_font.render("เลือกระดับความยาก", True, LIGHT_TEXT)
        self.screen.blit(subtitle, (50, 200))

        # Level cards
        mouse_pos = self.game.mouse_pos()
        for level, card, color in self.level_cards:
            cfg = CHALLENGE_LEVELS[level]
            card.draw(self.screen, self.label_font, selected=False)

            # Card details
            card_rect = card.rect
            desc = self.desc_font.render(cfg["description"], True, LIGHT_TEXT)
            self.screen.blit(desc, (card_rect.x + 20, card_rect.y + 80))

            rounds = self.desc_font.render(f"{cfg['rounds']} ข้อ • {cfg['category_mix']} หมวด", True, LIGHT_TEXT)
            self.screen.blit(rounds, (card_rect.x + 20, card_rect.y + 130))

        # Back button
        back_btn = Button(
            pygame.Rect(50, HEIGHT - 120, 200, 70),
            "← กลับ",
            SECONDARY,
            WHITE,
            radius=20
        )
        back_btn.draw(self.screen, self.label_font, hovered=back_btn.collide(mouse_pos))
