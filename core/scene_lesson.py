import pygame, random, time, math
from core.ui import Button, draw_status, HeaderUI, ProgressBar, Chip
from config import *
from core.data_loader import load_lessons
from core.audio import Recorder, PathummaASR
from rapidfuzz import fuzz

class MenuScene:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.font = pygame.font.Font(FONT_PATH, 48)
        self.subfont = pygame.font.Font(FONT_PATH, 28)
        self.btnfont = pygame.font.Font(FONT_PATH, 32)
        self.dialect = "central"
        self.dialect_btns = [
            Button(pygame.Rect(120+i*140, 340, 120, 50), DIALECT_LABELS[d], bg=[GREEN, BLUE, ORANGE, PINK][i], fg=WHITE, radius=24)
            for i, d in enumerate(["central", "northern", "isan", "southern"])
        ]
        self.start_btn = Button(pygame.Rect(WIDTH//2-160, 420, 140, 60), "เริ่มฝึก", bg=GREEN, fg=WHITE, radius=28)
        self.free_btn = Button(pygame.Rect(WIDTH//2+20, 420, 180, 60), "โหมดพูดอิสระ", bg=BLUE, fg=WHITE, radius=28)

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return "EXIT"
                if e.type == pygame.MOUSEBUTTONDOWN:
                    for i, btn in enumerate(self.dialect_btns):
                        if btn.rect.collidepoint(e.pos):
                            self.dialect = ["central", "northern", "isan", "southern"][i]
                    if self.start_btn.rect.collidepoint(e.pos):
                        self.game.dialect = self.dialect
                        return "LESSON"
                    if self.free_btn.rect.collidepoint(e.pos):
                        self.game.dialect = self.dialect
                        return "FREESPEAK"

            self.screen.fill(WHITE)
            # Title
            title = self.font.render("ภาษาถิ่นไทย", True, BLACK)
            self.screen.blit(title, (WIDTH//2-title.get_width()//2, 120))
            subtitle = self.subfont.render("ฝึกสำเนียงไทยแบบโต้ตอบด้วยเสียง", True, GRAY)
            self.screen.blit(subtitle, (WIDTH//2-subtitle.get_width()//2, 180))

            # Dialect selector
            for i, btn in enumerate(self.dialect_btns):
                hovered = btn.rect.collidepoint(pygame.mouse.get_pos())
                btn.draw(self.screen, self.btnfont, hovered=hovered)
                if ["central", "northern", "isan", "southern"][i] == self.dialect:
                    pygame.draw.rect(self.screen, YELLOW, btn.rect, 4, border_radius=btn.radius)

            # Main buttons
            self.start_btn.draw(self.screen, self.btnfont, hovered=self.start_btn.rect.collidepoint(pygame.mouse.get_pos()))
            self.free_btn.draw(self.screen, self.btnfont, hovered=self.free_btn.rect.collidepoint(pygame.mouse.get_pos()))

            pygame.display.flip()
            clock.tick(FPS)

class LessonScene:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.font = pygame.font.Font(FONT_PATH, 32)
        self.smallfont = pygame.font.Font(FONT_PATH, 22)
        self.cards = load_lessons("data/lessons_default.json")
        random.shuffle(self.cards)
        self.index = 0
        self.asr = PathummaASR()
        self.rec = Recorder(SAMPLE_RATE, CHANNELS, MAX_SPEAK_SECONDS)
        self.recording = False
        self.feedback = None
        self.hearts = 3
        self.xp = 0
        self.streak = game.streak if hasattr(game, "streak") else 0
        self.dialect = getattr(game, "dialect", "central")
        self.header = HeaderUI(self.xp, self.streak, self.hearts, self.dialect, self.index, len(self.cards))
        self.last_action_msg = ""
        self.last_action_time = 0
        self.anim_phase = 0

    def evaluate(self, text, targets):
        best = max(fuzz.partial_ratio(text, t) for t in targets)
        if best >= ASR_THRESHOLD_OK: return "ok", best
        if best >= ASR_THRESHOLD_PARTIAL: return "partial", best
        return "bad", best

    def play_feedback_sound(self, kind):
        if kind == "ok":
            pygame.mixer.Sound("assets/ok.wav").play()
        elif kind == "bad":
            pygame.mixer.Sound("assets/bad.wav").play()

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return "EXIT"
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE: return "MENU"
                    if e.key == pygame.K_m:
                        if not self.recording:
                            self.rec.start()
                            self.recording = True
                            self.last_action_msg = "เริ่มบันทึกเสียง"
                            self.last_action_time = time.time()
                        else:
                            wav = self.rec.stop_to_wav()
                            self.recording = False
                            self.last_action_msg = "กำลังประมวลผล..."
                            self.last_action_time = time.time()
                            text = self.asr.transcribe(wav)
                            kind, score = self.evaluate(text, self.cards[self.index]["targets"][self.dialect])
                            self.feedback = (kind, score, text)
                            self.play_feedback_sound(kind)
                            if kind == "ok":
                                self.xp += 10
                                self.streak += 1
                            elif kind == "partial":
                                self.xp += 5
                            else:
                                self.hearts -= 1
                                self.streak = 0
                            self.index += 1
                            if self.index >= len(self.cards) or self.hearts <= 0:
                                self.game.streak = self.streak
                                self.game.xp = self.xp
                                return "SUMMARY"

            self.screen.fill(WHITE)
            self.header.update(self.xp, self.streak, self.hearts, self.dialect, self.index, len(self.cards))
            self.header.draw(self.screen)

            card = self.cards[self.index]
            # Card UI
            card_rect = pygame.Rect(60, 100, WIDTH-120, 260)
            pygame.draw.rect(self.screen, GRAY, card_rect, border_radius=32)
            pygame.draw.rect(self.screen, BLUE, card_rect, 4, border_radius=32)
            prompt = self.font.render(card["prompt"], True, BLACK)
            self.screen.blit(prompt, (card_rect.x+32, card_rect.y+32))

            # Example answers as chips
            chip_y = card_rect.y + 100
            for i, ans in enumerate(card["targets"][self.dialect][:3]):
                Chip(ans, ORANGE, WHITE).draw(self.screen, self.smallfont, card_rect.x+32+i*160, chip_y)

            # Record status indicator
            status_rect = pygame.Rect(card_rect.x, card_rect.y+card_rect.height+20, card_rect.width, 50)
            if self.recording:
                # Blinking red
                blink = int(math.sin(time.time()*6)*60+195)
                pygame.draw.rect(self.screen, (255, blink, blink), status_rect, border_radius=18)
                status = self.smallfont.render("🟥 กำลังบันทึกเสียง...", True, WHITE)
            elif self.feedback and time.time()-self.last_action_time < 2:
                pygame.draw.rect(self.screen, YELLOW, status_rect, border_radius=18)
                status = self.smallfont.render("🟨 กำลังประมวลผล...", True, BLACK)
            else:
                pygame.draw.rect(self.screen, GREEN, status_rect, border_radius=18)
                status = self.smallfont.render("🟩 กด M เพื่อบันทึกเสียง", True, WHITE)
            self.screen.blit(status, (status_rect.x+24, status_rect.y+10))

            # After recording: show feedback
            if self.feedback:
                fb_rect = pygame.Rect(card_rect.x, status_rect.y+60, card_rect.width, 90)
                kind, score, text = self.feedback
                if kind == "ok":
                    pygame.draw.rect(self.screen, GREEN, fb_rect, border_radius=18)
                    fb_txt = "✅ ยอดเยี่ยม! +10 XP"
                elif kind == "partial":
                    pygame.draw.rect(self.screen, ORANGE, fb_rect, border_radius=18)
                    fb_txt = "⚠️ ใกล้แล้ว! +5 XP"
                else:
                    pygame.draw.rect(self.screen, RED, fb_rect, border_radius=18)
                    fb_txt = "❌ ลองใหม่! -1 ❤️"
                fb = self.smallfont.render(fb_txt, True, WHITE)
                self.screen.blit(fb, (fb_rect.x+24, fb_rect.y+10))
                spoken = self.smallfont.render(f"คุณพูดว่า: '{text}'", True, BLACK)
                self.screen.blit(spoken, (fb_rect.x+24, fb_rect.y+45))

            # Progress bar
            ProgressBar(self.index, len(self.cards)).draw(self.screen, WIDTH//2-180, HEIGHT-60, 360, 24)

            pygame.display.flip()
            clock.tick(FPS)
