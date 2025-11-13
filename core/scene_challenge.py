import random
import pygame
from config import *


class ChallengeScene:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.title_font = pygame.font.Font(FONT_PATH, 54)
        self.font = pygame.font.Font(FONT_PATH, 28)
        self.small_font = pygame.font.Font(FONT_PATH, 20)
        self.level_order = ["easy", "medium", "hard"]
        self.card_rects = self._build_cards()

    def _build_cards(self):
        cards = []
        width = 340
        height = 220
        gap = 30
        start_x = (WIDTH - (len(self.level_order) * width + (len(self.level_order) - 1) * gap)) // 2
        y = 280
        for idx, level in enumerate(self.level_order):
            rect = pygame.Rect(start_x + idx * (width + gap), y, width, height)
            cards.append((level, rect))
        return cards

    def _draw_background(self):
        self.screen.fill((16, 20, 40))
        pygame.draw.circle(self.screen, (48, 87, 219), (220, 190), 220)
        pygame.draw.circle(self.screen, (19, 145, 161), (WIDTH - 140, 80), 180)
        pygame.draw.circle(self.screen, (226, 148, 35), (WIDTH - 200, HEIGHT - 140), 220)

    def _draw_card(self, level, rect, hovered=False):
        cfg = CHALLENGE_LEVELS[level]
        colors = {
            "easy": ((90, 206, 172), (22, 82, 74)),
            "medium": ((255, 210, 114), (117, 79, 0)),
            "hard": ((255, 128, 128), (110, 12, 30)),
        }
        bg, fg = colors.get(level, ((255, 255, 255), (30, 30, 30)))
        base = tuple(min(255, int(c * (1.08 if hovered else 1))) for c in bg)
        pygame.draw.rect(self.screen, base, rect, border_radius=28)
        pygame.draw.rect(self.screen, (255, 255, 255), rect, 3, border_radius=28)
        title = self.font.render(f"ด่าน{cfg['label']}", True, fg)
        self.screen.blit(title, (rect.x + 24, rect.y + 24))
        desc_rect = pygame.Rect(rect.x + 24, rect.y + 70, rect.width - 48, rect.height - 110)
        self._draw_multiline(cfg["description"], desc_rect, self.small_font, fg)
        rounds_text = self.small_font.render(
            f"{cfg['rounds']} การ์ด • ผสม {cfg['category_mix']} หมวด", True, fg
        )
        self.screen.blit(rounds_text, (rect.x + 24, rect.bottom - 50))
        badge = self.small_font.render("เริ่มทันที ▶", True, fg)
        self.screen.blit(badge, (rect.x + rect.width - badge.get_width() - 24, rect.bottom - 50))

    def _draw_multiline(self, text, rect, font, color):
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if font.size(candidate)[0] <= rect.width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        y = rect.y
        for line in lines:
            surface = font.render(line, True, color)
            self.screen.blit(surface, (rect.x, y))
            y += surface.get_height() + 6

    def _start_challenge(self, level):
        self.game.state["mode"] = "challenge"
        self.game.state["challenge_level"] = level
        mix_count = CHALLENGE_LEVELS[level]["category_mix"]
        available = [c["key"] for c in CONTENT_CATEGORIES]
        random.shuffle(available)
        self.game.state["challenge_mix"] = available[:mix_count]
        return "LESSON"

    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return "EXIT"
                if e.type == pygame.VIDEORESIZE:
                    self.game.handle_resize(e)
                    continue
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    return "MENU"
                pointer = self.game.logical_pos(e.pos) if hasattr(e, "pos") else None
                if e.type == pygame.MOUSEBUTTONDOWN and pointer:
                    for level, rect in self.card_rects:
                        if rect.collidepoint(pointer):
                            return self._start_challenge(level)

            self._draw_background()
            headline = self.title_font.render("Challenge Mode", True, WHITE)
            self.screen.blit(headline, headline.get_rect(center=(WIDTH // 2, 140)))
            subtitle = self.font.render(
                "เลือกด่านที่ชอบ — ระบบจะสุ่มบทสนทนาจากหลายหมวดหมู่", True, WHITE
            )
            self.screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 200)))

            mouse_pos = self.game.mouse_pos()
            for level, rect in self.card_rects:
                self._draw_card(level, rect, hovered=rect.collidepoint(mouse_pos))

            helper = self.small_font.render("กด Esc เพื่อกลับเมนู", True, (200, 212, 230))
            self.screen.blit(helper, helper.get_rect(center=(WIDTH // 2, HEIGHT - 80)))

            self.game.present()
