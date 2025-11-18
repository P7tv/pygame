import pygame
from config import *
from core.ui import Button, PRIMARY, SECONDARY, ACCENT, LIGHT_TEXT, DARK_BG, Card, BORDER_COLOR
from core.audio import PathummaASR
from core.sound_manager import SoundManager


class MenuScene:
    """ฉากเมนูหลัก: เลือกสำเนียง หมวด และโหมดการเล่น"""

    def __init__(self, game):
        self.game = game
        self.screen = game.screen

        # ฟอนต์หลักที่ใช้ในหัวข้อ ป้าย และปุ่ม
        self.title_font = pygame.font.Font(FONT_PATH, 64)
        self.subtitle_font = pygame.font.Font(FONT_PATH, 32)
        self.label_font = pygame.font.Font(FONT_PATH, 32)
        self.button_font = pygame.font.Font(FONT_PATH, 40)

        # ค่าที่เลือกล่าสุด (ใช้ highlight ให้ผู้เล่นเห็น)
        self.selected_dialect = self.game.state.get("dialect", DIALECTS[0])
        self.selected_category = self.game.state.get("category", DEFAULT_CATEGORY_KEY)

        # เริ่มโหลดโมเดล ASR ล่วงหน้าตั้งแต่หน้าเมนู
        self.asr = PathummaASR()
        self.asr.start_loading()

        # ประกอบปุ่มทั้งหมด
        self._create_buttons()
    # หลีกเลี่ยงเสียง hover ในหน้านี้ ให้มีเฉพาะเสียงคลิก

    def _create_buttons(self):
        """จัดเลย์เอาต์ปุ่มหลัก/ปุ่มสำเนียงและการ์ดหมวดหมู่"""
        # ปุ่มคำสั่งหลักด้านล่าง 3 ปุ่ม
        btn_width = 500
        btn_height = 130
        btn_gap = 50
        total_w = btn_width * 3 + btn_gap * 2
        start_x = (WIDTH - total_w) // 2

        self.lesson_btn = Button(
            pygame.Rect(start_x, HEIGHT - 260, btn_width, btn_height),
            "เริ่มบทเรียน",
            PRIMARY, WHITE
        )
        self.challenge_btn = Button(
            pygame.Rect(start_x + btn_width + btn_gap, HEIGHT - 260, btn_width, btn_height),
            "โหมดชาเลนจ์",
            SECONDARY, WHITE
        )
        self.free_btn = Button(
            pygame.Rect(start_x + (btn_width + btn_gap) * 2, HEIGHT - 260, btn_width, btn_height),
            "พูดอิสระ",
            ACCENT, WHITE
        )

        # ปุ่มเลือกสำเนียง 4 ปุ่มเรียงแนวนอน
        dialect_btn_width = 260
        dialect_btn_height = 100
        dialect_btn_gap = 36
        total_d_w = dialect_btn_width * 4 + dialect_btn_gap * 3
        start_dx = (WIDTH - total_d_w) // 2

        self.dialect_buttons = []
        colors = [PRIMARY, ACCENT, SECONDARY, (200, 50, 100)]
        for i, (key, color) in enumerate(zip(DIALECTS, colors)):
            btn = Button(
                pygame.Rect(start_dx + i * (dialect_btn_width + dialect_btn_gap), 230, dialect_btn_width, dialect_btn_height),
                DIALECT_LABELS[key],
                color, WHITE, radius=16
            )
            self.dialect_buttons.append((key, btn))

        # การ์ดหมวดหมู่จัดเป็นตาราง 3 คอลัมน์
        self.category_cards = []
        cols = 3
        card_width = 280
        card_height = 160
        card_gap = 36
        total_cw = card_width * cols + card_gap * (cols - 1)
        start_cx = (WIDTH - total_cw) // 2

        for idx, cat in enumerate(CONTENT_CATEGORIES):
            row = idx // cols
            col = idx % cols
            x = start_cx + col * (card_width + card_gap)
            y = 390 + row * (card_height + card_gap)
            card = Card(cat["label"].split()[0], x, y, card_width, card_height)
            self.category_cards.append((cat, card))

    def run(self):
        """ลูป event สำหรับเมนู: คลิกเพื่อเลือกค่าหรือตัดสินใจเข้าโหมด"""
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return "EXIT"
                if e.type == pygame.VIDEORESIZE:
                    self.game.handle_resize(e)

                pointer = self.game.logical_pos(e.pos) if hasattr(e, "pos") else None  # พิกัดเมาส์ในระบบ canvas
                # ไม่เล่นเสียง hover: ให้มีเฉพาะตอนคลิกเพื่อยืนยันการเลือก

                if e.type == pygame.MOUSEBUTTONDOWN and pointer:
                    sound_mgr = SoundManager()

                    # ปุ่มคำสั่งหลัก
                    if self.lesson_btn.collide(pointer):
                        sound_mgr.play_ok()
                        return "LESSON"
                    if self.challenge_btn.collide(pointer):
                        sound_mgr.play_ok()
                        return "CHALLENGE"
                    if self.free_btn.collide(pointer):
                        sound_mgr.play_ok()
                        return "FREE"

                    # ปุ่มเลือกสำเนียง
                    for key, btn in self.dialect_buttons:
                        if btn.collide(pointer):
                            sound_mgr.play_bad()
                            self.selected_dialect = key
                            self.game.state["dialect"] = key
                            self.game.dialect = key

                    # การ์ดเลือกหมวด
                    for cat, card in self.category_cards:
                        if card.collide(pointer):
                            sound_mgr.play_bad()
                            self.selected_category = cat["key"]
                            self.game.state["category"] = cat["key"]
                            self.game.category = cat["key"]

            self._draw()
            self.game.present()

    def _draw(self):
        """วาดสไตล์เมนูคล้าย Duolingo พร้อมแสดงสถานะโมเดล ASR"""
        # ฉากหลังสีเทาอ่อน
        self.screen.fill(DARK_BG)

        # ส่วนหัวสีขาวพร้อมเส้นคั่น
        pygame.draw.rect(self.screen, WHITE, (0, 0, WIDTH, 150))
        pygame.draw.line(self.screen, (220, 220, 220), (0, 149), (WIDTH, 149), 1)

        # ชื่อโปรเจกต์
        title = self.title_font.render("ภาษาถิ่นไทย", True, PRIMARY)
        self.screen.blit(title, (50, 40))

        # ป้ายอธิบายโซนเลือกสำเนียง
        dialect_label = self.label_font.render("เลือกสำเนียง", True, LIGHT_TEXT)
        self.screen.blit(dialect_label, (50, 170))

        # ปุ่มสำเนียง (highlight ตามตัวเลือกปัจจุบัน)
        mouse_pos = self.game.mouse_pos()
        for key, btn in self.dialect_buttons:
            selected = key == self.selected_dialect
            btn.draw(self.screen, self.label_font, hovered=selected or btn.collide(mouse_pos))

        # ป้ายหมวดบทเรียน
        category_label = self.label_font.render("เลือกหมวดหมู่", True, LIGHT_TEXT)
        self.screen.blit(category_label, (50, 290))

        # การ์ดหมวด: ถ้าเลือกอยู่ให้แสดงพื้นสีเข้ม
        for cat, card in self.category_cards:
            selected = cat["key"] == self.selected_category
            card.draw(self.screen, self.label_font, selected=selected)

        # ปุ่มคำสั่งสามโหมด
        self.lesson_btn.draw(self.screen, self.button_font, hovered=self.lesson_btn.collide(mouse_pos))
        self.challenge_btn.draw(self.screen, self.button_font, hovered=self.challenge_btn.collide(mouse_pos))
        self.free_btn.draw(self.screen, self.button_font, hovered=self.free_btn.collide(mouse_pos))

        # มุมขวาบนโชว์สถานะ ASR พร้อมใส่อนิเมชันจุดกระพริบเมื่อกำลังโหลด
        status = self.asr.get_status() if hasattr(self, 'asr') else 'idle'
        status_text = f"ASR: {status}"
        small = pygame.font.Font(FONT_PATH, 18)
        txt = small.render(status_text, True, LIGHT_TEXT)
        rect = txt.get_rect()
        rect.topright = (WIDTH - 20, 20)
        # พื้นหลังโปร่งขาวเล็ก ๆ รองรับข้อความสถานะ
        bg_rect = pygame.Rect(rect.x - 10, rect.y - 6, rect.w + 20, rect.h + 12)
        pygame.draw.rect(self.screen, WHITE, bg_rect, border_radius=10)
        pygame.draw.rect(self.screen, BORDER_COLOR, bg_rect, 1, border_radius=10)
        self.screen.blit(txt, rect)
        # ถ้ายังโหลดหรือกำลังถอดเสียงให้แสดงจุดกระพริบเป็นตัวจับเวลา
        if status in ("loading", "transcribing"):
            tick = pygame.time.get_ticks() // 250
            dots = (tick % 4)
            dots_txt = small.render("." * dots, True, PRIMARY)
            self.screen.blit(dots_txt, (rect.right + 4, rect.y))
