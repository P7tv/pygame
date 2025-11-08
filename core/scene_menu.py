import pygame
from config import *
from core.ui import Button

class MenuScene:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.title_font = pygame.font.Font(FONT_PATH, 44)
        self.font = pygame.font.Font(FONT_PATH, 30)
        self.small_font = pygame.font.Font(FONT_PATH, 22)
        self.selected_dialect = self.game.state.get("dialect", DIALECTS[0])
        self.selected_category = self.game.state.get("category", DEFAULT_CATEGORY_KEY)
        self.dialect_rects = []
        self.category_rects = []
        self._build_layouts()
        self.buttons = self._build_action_buttons()

    def _build_layouts(self):
        self.dialect_rects.clear()
        button_w = 150
        spacing = 18
        total_width = (button_w * len(DIALECTS)) + spacing * (len(DIALECTS) - 1)
        start_x = (WIDTH - total_width) // 2
        for idx, key in enumerate(DIALECTS):
            rect = pygame.Rect(
                start_x + idx * (button_w + spacing),
                220,
                button_w,
                48,
            )
            self.dialect_rects.append((key, rect))

        self.category_rects.clear()
        cols = 2
        col_gap = 40
        col_width = 360
        row_height = 64
        rows = (len(CONTENT_CATEGORIES) + cols - 1) // cols
        total_width = cols * col_width + (cols - 1) * col_gap
        start_x = (WIDTH - total_width) // 2
        start_y = 300
        for idx, cat in enumerate(CONTENT_CATEGORIES):
            row = idx // cols
            col = idx % cols
            rect = pygame.Rect(
                start_x + col * (col_width + col_gap),
                start_y + row * (row_height + 16),
                col_width,
                row_height,
            )
            self.category_rects.append((cat, rect))
        self.category_area_bottom = (
            start_y + rows * (row_height + 16) - 16
        )

    def _build_action_buttons(self):
        top = self.category_area_bottom + 40
        button_width = 340
        button_height = 64
        center_x = WIDTH // 2
        lesson_rect = pygame.Rect(
            center_x - button_width - 12,
            top,
            button_width,
            button_height,
        )
        free_rect = pygame.Rect(
            center_x + 12,
            top,
            button_width,
            button_height,
        )
        return {
            "lesson": Button(lesson_rect, "เริ่มบทเรียน ▶", GREEN, WHITE, radius=32),
            "free": Button(free_rect, "โหมดพูดอิสระ 🎤", BLUE, WHITE, radius=32),
        }

    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return "EXIT"
                if e.type == pygame.VIDEORESIZE:
                    self.game.handle_resize(e)
                    continue
                pointer = self.game.logical_pos(e.pos) if hasattr(e, "pos") else None
                if e.type == pygame.MOUSEBUTTONDOWN:
                    if pointer and self.buttons["lesson"].rect.collidepoint(pointer):
                        return "LESSON"
                    if pointer and self.buttons["free"].rect.collidepoint(pointer):
                        return "FREE"
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

            self.screen.fill(WHITE)
            panel_top = 160
            panel_bottom = max(self.category_area_bottom + 110, panel_top + 320)
            panel_rect = pygame.Rect(80, panel_top, WIDTH - 160, panel_bottom - panel_top)
            shadow_rect = panel_rect.move(0, 6)
            pygame.draw.rect(self.screen, (220, 230, 240), shadow_rect, border_radius=36)
            pygame.draw.rect(self.screen, (245, 248, 255), panel_rect, border_radius=36)

            title = self.title_font.render("ภาษาถิ่นไทย", True, BLACK)
            self.screen.blit(title, title.get_rect(center=(WIDTH//2, panel_top + 36)))

            subtitle = self.small_font.render("เลือกสำเนียงและหมวดหมู่ก่อนเริ่มบทเรียน", True, (70, 90, 120))
            self.screen.blit(subtitle, subtitle.get_rect(center=(WIDTH//2, panel_top + 80)))

            # Dialect selection
            dialect_label = self.font.render("เลือกสำเนียง", True, BLACK)
            self.screen.blit(dialect_label, dialect_label.get_rect(center=(WIDTH//2, 190)))
            for key, rect in self.dialect_rects:
                selected = key == self.selected_dialect
                base_color = (204, 245, 212) if selected else (233, 243, 233)
                border_color = GREEN if selected else (170, 210, 176)
                pygame.draw.rect(self.screen, base_color, rect, border_radius=22)
                pygame.draw.rect(self.screen, border_color, rect, border_radius=22, width=2)
                label = self.small_font.render(DIALECT_LABELS.get(key, key), True, (30, 80, 36))
                self.screen.blit(label, label.get_rect(center=rect.center))

            # Category selection
            cat_label = self.font.render("เลือกหมวดหมู่บทเรียน", True, BLACK)
            self.screen.blit(cat_label, cat_label.get_rect(center=(WIDTH//2, 250)))
            for cat, rect in self.category_rects:
                selected = cat["key"] == self.selected_category
                base_color = (184, 222, 255) if selected else (232, 244, 253)
                border_color = (35, 140, 215) if selected else (180, 210, 235)
                text_color = WHITE if selected else (30, 80, 120)
                pygame.draw.rect(self.screen, base_color, rect, border_radius=24)
                pygame.draw.rect(self.screen, border_color, rect, width=2, border_radius=24)
                label = self.small_font.render(cat["label"], True, text_color)
                self.screen.blit(label, label.get_rect(center=rect.center))

            # Main buttons
            mouse_pos = self.game.mouse_pos()
            for b in self.buttons.values():
                b.draw(self.screen, self.font, hovered=b.rect.collidepoint(mouse_pos))
            self.game.present()
