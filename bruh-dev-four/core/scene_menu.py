import pygame
from config import *
from core.ui import Button, PRIMARY, SECONDARY, ACCENT, LIGHT_TEXT, DARK_BG, Card, BORDER_COLOR
from core.audio import PathummaASR
from core.sound_manager import SoundManager


class MenuScene:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen

        # Fonts
        self.title_font = pygame.font.Font(FONT_PATH, 64)
        self.subtitle_font = pygame.font.Font(FONT_PATH, 32)
        self.label_font = pygame.font.Font(FONT_PATH, 28)
        self.button_font = pygame.font.Font(FONT_PATH, 28)

        # State
        self.selected_dialect = self.game.state.get("dialect", DIALECTS[0])
        self.selected_category = self.game.state.get("category", DEFAULT_CATEGORY_KEY)

        # Start loading ASR
        self.asr = PathummaASR()
        self.asr.start_loading()

        # Create buttons
        self._create_buttons()
    # (no hover SFX here; clicks only)

    def _create_buttons(self):
        """Create all UI buttons"""
        # Main action buttons (bottom)
        btn_width = 280
        btn_height = 60
        btn_gap = 20
        total_w = btn_width * 3 + btn_gap * 2
        start_x = (WIDTH - total_w) // 2

        self.lesson_btn = Button(
            pygame.Rect(start_x, HEIGHT - 150, btn_width, btn_height),
            "เริ่มบทเรียน",
            PRIMARY, WHITE
        )
        self.challenge_btn = Button(
            pygame.Rect(start_x + btn_width + btn_gap, HEIGHT - 150, btn_width, btn_height),
            "โหมดชาเลนจ์",
            SECONDARY, WHITE
        )
        self.free_btn = Button(
            pygame.Rect(start_x + (btn_width + btn_gap) * 2, HEIGHT - 150, btn_width, btn_height),
            "พูดอิสระ",
            ACCENT, WHITE
        )

        # Dialect buttons (4 buttons side by side)
        dialect_btn_width = 140
        dialect_btn_height = 50
        dialect_btn_gap = 16
        total_d_w = dialect_btn_width * 4 + dialect_btn_gap * 3
        start_dx = (WIDTH - total_d_w) // 2

        self.dialect_buttons = []
        colors = [PRIMARY, ACCENT, SECONDARY, (200, 50, 100)]
        for i, (key, color) in enumerate(zip(DIALECTS, colors)):
            btn = Button(
                pygame.Rect(start_dx + i * (dialect_btn_width + dialect_btn_gap), 200, dialect_btn_width, dialect_btn_height),
                DIALECT_LABELS[key],
                color, WHITE, radius=10
            )
            self.dialect_buttons.append((key, btn))

        # Category cards
        self.category_cards = []
        cols = 3
        card_width = 180
        card_height = 100
        card_gap = 24
        total_cw = card_width * cols + card_gap * (cols - 1)
        start_cx = (WIDTH - total_cw) // 2

        for idx, cat in enumerate(CONTENT_CATEGORIES):
            row = idx // cols
            col = idx % cols
            x = start_cx + col * (card_width + card_gap)
            y = 320 + row * (card_height + card_gap)
            card = Card(cat["label"].split()[0], x, y, card_width, card_height)
            self.category_cards.append((cat, card))

    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return "EXIT"
                if e.type == pygame.VIDEORESIZE:
                    self.game.handle_resize(e)

                pointer = self.game.logical_pos(e.pos) if hasattr(e, "pos") else None
                # no hover SFX: play sounds on clicks only

                if e.type == pygame.MOUSEBUTTONDOWN and pointer:
                    sound_mgr = SoundManager()

                    # Main action buttons
                    if self.lesson_btn.collide(pointer):
                        sound_mgr.play_ok()
                        return "LESSON"
                    if self.challenge_btn.collide(pointer):
                        sound_mgr.play_ok()
                        return "CHALLENGE"
                    if self.free_btn.collide(pointer):
                        sound_mgr.play_ok()
                        return "FREE"

                    # Dialect buttons
                    for key, btn in self.dialect_buttons:
                        if btn.collide(pointer):
                            sound_mgr.play_bad()
                            print(f"Selected dialect: {DIALECT_LABELS[key]}")
                            self.selected_dialect = key
                            self.game.state["dialect"] = key
                            self.game.dialect = key

                    # Category cards
                    for cat, card in self.category_cards:
                        if card.collide(pointer):
                            sound_mgr.play_bad()
                            print(f"Selected category: {cat['label']}")
                            print(self.selected_category)
                            self.selected_category = cat["key"]
                            print(self.selected_category)
                            print("---------")
                            self.game.state["category"] = cat["key"]
                            print(self.game.state["category"])
                            self.game.category = cat["key"]

            self._draw()
            self.game.present()

    def _draw(self):
        """Draw the menu scene"""
        # Background
        self.screen.fill(DARK_BG)

        # Header white section
        pygame.draw.rect(self.screen, WHITE, (0, 0, WIDTH, 150))
        pygame.draw.line(self.screen, (220, 220, 220), (0, 149), (WIDTH, 149), 1)

        # Title
        title = self.title_font.render("ภาษาถิ่นไทย", True, PRIMARY)
        self.screen.blit(title, (50, 40))

        # Dialect selector label
        dialect_label = self.label_font.render("เลือกสำเนียง", True, LIGHT_TEXT)
        self.screen.blit(dialect_label, (50, 170))

        # Dialect buttons
        mouse_pos = self.game.mouse_pos()
        for key, btn in self.dialect_buttons:
            selected = key == self.selected_dialect
            btn.draw(self.screen, self.label_font, hovered=selected or btn.collide(mouse_pos))

        # Category label
        category_label = self.label_font.render("เลือกหมวดหมู่", True, LIGHT_TEXT)
        self.screen.blit(category_label, (50, 290))

        # Category cards
        for cat, card in self.category_cards:
            selected = cat["key"] == self.selected_category
            card.draw(self.screen, self.label_font, selected=selected)

        # Action buttons
        self.lesson_btn.draw(self.screen, self.button_font, hovered=self.lesson_btn.collide(mouse_pos))
        self.challenge_btn.draw(self.screen, self.button_font, hovered=self.challenge_btn.collide(mouse_pos))
        self.free_btn.draw(self.screen, self.button_font, hovered=self.free_btn.collide(mouse_pos))

        # ASR status indicator (top-right)
        status = self.asr.get_status() if hasattr(self, 'asr') else 'idle'
        status_text = f"ASR: {status}"
        small = pygame.font.Font(FONT_PATH, 18)
        txt = small.render(status_text, True, LIGHT_TEXT)
        rect = txt.get_rect()
        rect.topright = (WIDTH - 20, 20)
        # small background
        bg_rect = pygame.Rect(rect.x - 10, rect.y - 6, rect.w + 20, rect.h + 12)
        pygame.draw.rect(self.screen, WHITE, bg_rect, border_radius=10)
        pygame.draw.rect(self.screen, BORDER_COLOR, bg_rect, 1, border_radius=10)
        self.screen.blit(txt, rect)
        # simple spinner when loading/transcribing
        if status in ("loading", "transcribing"):
            tick = pygame.time.get_ticks() // 250
            dots = (tick % 4)
            dots_txt = small.render("." * dots, True, PRIMARY)
            self.screen.blit(dots_txt, (rect.right + 4, rect.y))
