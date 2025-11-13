import pygame
from config import *
from core.ui import Button


class MenuScene:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.title_font = pygame.font.Font(FONT_PATH, 60)
        self.tagline_font = pygame.font.Font(FONT_PATH, 28)
        self.section_font = pygame.font.Font(FONT_PATH, 32)
        self.font = pygame.font.Font(FONT_PATH, 26)
        self.small_font = pygame.font.Font(FONT_PATH, 20)
        self.selected_dialect = self.game.state.get("dialect", DIALECTS[0])
        self.selected_category = self.game.state.get("category", DEFAULT_CATEGORY_KEY)
        self.hero_highlights = [
            ("⏱ 3-5 นาที / บท", (239, 246, 255), (50, 96, 165)),
            ("🎯 ฝึกพูดพร้อมฟีดแบ็ก", (237, 251, 243), (24, 120, 68)),
            ("📚 7 หมวดหลัก", (255, 246, 232), (171, 78, 0)),
        ]
        self.tip_cards = [
            ("เริ่มต้นเร็ว", "เลือกระดับและกดเริ่มบทเรียนได้ทันที"),
            ("ฝึกอิสระ", "ใช้โหมดพูดอิสระซ้อมออกเสียง"),
        ]
        self._build_layouts()
        self.buttons = self._build_action_buttons()

    def _build_layouts(self):
        self.hero_rect = pygame.Rect(80, 60, WIDTH - 160, 210)
        left_width = 520
        right_width = WIDTH - left_width - 220
        panel_top = self.hero_rect.bottom + 30
        panel_height = 480
        self.left_panel = pygame.Rect(80, panel_top, left_width, panel_height)
        self.right_panel = pygame.Rect(self.left_panel.right + 30, panel_top, right_width, panel_height)

        # Dialect chips stack
        self.dialect_rects = []
        chip_height = 68
        gap = 14
        for idx, key in enumerate(DIALECTS):
            rect = pygame.Rect(
                self.left_panel.x + 26,
                self.left_panel.y + 110 + idx * (chip_height + gap),
                self.left_panel.width - 52,
                chip_height,
            )
            self.dialect_rects.append((key, rect))

        # Category cards in a responsive grid (3 columns by default)
        self.category_rects = []
        cols = 3
        card_gap = 20
        card_width = (self.right_panel.width - (cols + 1) * card_gap) // cols
        card_height = 120
        start_x = self.right_panel.x + card_gap
        start_y = self.right_panel.y + 110
        for idx, cat in enumerate(CONTENT_CATEGORIES):
            row = idx // cols
            col = idx % cols
            rect = pygame.Rect(
                start_x + col * (card_width + card_gap),
                start_y + row * (card_height + card_gap),
                card_width,
                card_height,
            )
            self.category_rects.append((cat, rect))
        if self.category_rects:
            self.category_area_bottom = self.category_rects[-1][1].bottom
        else:
            self.category_area_bottom = self.right_panel.bottom

    def _build_action_buttons(self):
        top = max(self.left_panel.bottom, self.category_area_bottom) + 36
        button_width = 320
        button_height = 72
        gap = 22
        total_width = button_width * 3 + gap * 2
        start_x = (WIDTH - total_width) // 2
        lesson_rect = pygame.Rect(start_x, top, button_width, button_height)
        challenge_rect = pygame.Rect(start_x + button_width + gap, top, button_width, button_height)
        free_rect = pygame.Rect(start_x + (button_width + gap) * 2, top, button_width, button_height)
        return {
            "lesson": Button(lesson_rect, "เริ่มบทเรียน ▶", GREEN, WHITE, radius=34),
            "challenge": Button(challenge_rect, "โหมดชาเลนจ์ ⚡️", ORANGE, WHITE, radius=34),
            "free": Button(free_rect, "โหมดพูดอิสระ 🎤", BLUE, WHITE, radius=34),
        }

    def _draw_background(self):
        self.screen.fill((234, 240, 255))
        pygame.draw.circle(self.screen, (214, 228, 255), (WIDTH - 150, 80), 220)
        pygame.draw.circle(self.screen, (229, 255, 248), (160, 40), 180)
        pygame.draw.circle(self.screen, (255, 240, 230), (WIDTH - 320, HEIGHT - 100), 260)

    def _draw_panel(self, rect, color=(255, 255, 255), radius=32, shadow=True):
        if shadow:
            pygame.draw.rect(self.screen, (200, 212, 230), rect.move(0, 6), border_radius=radius)
        pygame.draw.rect(self.screen, color, rect, border_radius=radius)

    def _draw_multiline(self, text, font, color, rect, line_gap=6):
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
            y += surface.get_height() + line_gap

    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return "EXIT"
                if e.type == pygame.VIDEORESIZE:
                    self.game.handle_resize(e)
                    continue
                pointer = self.game.logical_pos(e.pos) if hasattr(e, "pos") else None
                if e.type == pygame.MOUSEBUTTONDOWN:
                    if pointer and self.buttons["lesson"].rect.collidepoint(pointer):
                        return "LESSON"
                    if pointer and self.buttons["free"].rect.collidepoint(pointer):
                        return "FREE"
                    if pointer and self.buttons["challenge"].rect.collidepoint(pointer):
                        return "CHALLENGE"
                    for key, rect in self.dialect_rects:
                        if pointer and rect.collidepoint(pointer):
                            self.selected_dialect = key
                            self.game.state["dialect"] = key
                            self.game.dialect = key
                    for cat, rect in self.category_rects:
                        if pointer and rect.collidepoint(pointer):
                            self.selected_category = cat["key"]
                            self.game.state["category"] = self.selected_category
                            self.game.category = self.selected_category

                if e.type == pygame.KEYDOWN:
                    if pygame.K_F1 <= e.key <= pygame.K_F4:
                        idx = e.key - pygame.K_F1
                        if 0 <= idx < len(DIALECTS):
                            key = DIALECTS[idx]
                            self.selected_dialect = key
                            self.game.state["dialect"] = key
                            self.game.dialect = key

            self._draw_background()

            # Hero section
            self._draw_panel(self.hero_rect, color=(247, 250, 255), radius=40)
            title = self.title_font.render("เรียนภาษาถิ่นไทยให้สนุก", True, (25, 39, 70))
            self.screen.blit(title, (self.hero_rect.x + 40, self.hero_rect.y + 32))
            tagline = self.tagline_font.render("ฝึกพูด ฟัง และโต้ตอบได้จริง เลือกสำเนียงและหมวดหมู่ที่สนใจ", True, (71, 85, 117))
            self.screen.blit(tagline, (self.hero_rect.x + 40, self.hero_rect.y + 110))
            for idx, (text, bg, fg) in enumerate(self.hero_highlights):
                chip_rect = pygame.Rect(
                    self.hero_rect.x + 40 + idx * 240,
                    self.hero_rect.bottom - 72,
                    220,
                    52,
                )
                pygame.draw.rect(self.screen, bg, chip_rect, border_radius=26)
                chip_text = self.small_font.render(text, True, fg)
                self.screen.blit(chip_text, chip_text.get_rect(center=chip_rect.center))

            # Left panel: dialects + tips
            self._draw_panel(self.left_panel, color=(255, 255, 255))
            dialect_label = self.section_font.render("เลือกสำเนียง", True, (25, 39, 70))
            self.screen.blit(dialect_label, (self.left_panel.x + 26, self.left_panel.y + 28))
            helper = self.small_font.render("สลับด้วยปุ่ม F1-F4 ได้เช่นกัน", True, (120, 135, 160))
            self.screen.blit(helper, (self.left_panel.x + 28, self.left_panel.y + 70))
            for key, rect in self.dialect_rects:
                selected = key == self.selected_dialect
                base_color = (214, 245, 224) if selected else (238, 247, 239)
                accent = (62, 159, 98) if selected else (160, 205, 172)
                pygame.draw.rect(self.screen, accent, rect, border_radius=26, width=2)
                inner_rect = rect.inflate(-8, -8)
                pygame.draw.rect(
                    self.screen,
                    base_color if selected else (255, 255, 255),
                    inner_rect,
                    border_radius=22,
                )
                name = DIALECT_LABELS.get(key, key)
                label = self.font.render(name, True, (26, 75, 44))
                self.screen.blit(label, (inner_rect.x + 24, inner_rect.y + 12))
                desc = self.small_font.render("สำเนียงเฉพาะพื้นที่ • มีตัวอย่างบทสนทนา", True, (85, 120, 95))
                self.screen.blit(desc, (inner_rect.x + 24, inner_rect.y + 40))

            # Quick tip cards
            tip_top = self.left_panel.bottom - 120
            for idx, (title_txt, desc_txt) in enumerate(self.tip_cards):
                rect = pygame.Rect(self.left_panel.x + 26 + idx * 232, tip_top, 212, 92)
                pygame.draw.rect(self.screen, (248, 250, 253), rect, border_radius=18)
                pygame.draw.rect(self.screen, (220, 230, 242), rect, width=1, border_radius=18)
                title_surface = self.small_font.render(title_txt, True, (30, 60, 90))
                self.screen.blit(title_surface, (rect.x + 14, rect.y + 12))
                desc_rect = pygame.Rect(rect.x + 14, rect.y + 40, rect.width - 28, rect.height - 48)
                self._draw_multiline(desc_txt, self.small_font, (95, 110, 130), desc_rect)

            # Right panel: categories grid
            self._draw_panel(self.right_panel, color=(255, 255, 255))
            cat_label = self.section_font.render("เลือกหมวดหมู่บทเรียน", True, (25, 39, 70))
            self.screen.blit(cat_label, (self.right_panel.x + 32, self.right_panel.y + 28))
            cat_helper = self.small_font.render("หมวดจะกำหนดบทสนทนาที่ใช้ซ้อม", True, (120, 135, 160))
            self.screen.blit(cat_helper, (self.right_panel.x + 34, self.right_panel.y + 70))
            for cat, rect in self.category_rects:
                selected = cat["key"] == self.selected_category
                base_color = (88, 142, 255) if selected else (244, 247, 255)
                overlay = (65, 105, 210) if selected else (214, 224, 245)
                pygame.draw.rect(self.screen, overlay, rect, border_radius=26)
                inner = rect.inflate(-6, -6)
                pygame.draw.rect(
                    self.screen,
                    base_color if selected else (255, 255, 255),
                    inner,
                    border_radius=22,
                )
                title_surface = self.font.render(cat["label"].split(" ")[0], True, (255, 255, 255) if selected else (40, 64, 110))
                self.screen.blit(title_surface, (inner.x + 24, inner.y + 18))
                desc_rect = pygame.Rect(inner.x + 24, inner.y + 56, inner.width - 48, inner.height - 70)
                desc_color = WHITE if selected else (80, 100, 135)
                self._draw_multiline(cat["label"], self.small_font, desc_color, desc_rect)

            # Main buttons
            mouse_pos = self.game.mouse_pos()
            for b in self.buttons.values():
                b.draw(self.screen, self.font, hovered=b.rect.collidepoint(mouse_pos))
            self.game.present()
