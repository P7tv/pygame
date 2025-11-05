import pygame, time, textwrap
from core.ui import TextField, Button
from core.audio import Recorder, PathummaASR
from rapidfuzz import fuzz
from config import *
from ai.dialect_advisor import roleplay_response

class FreeSpeakScene:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.font = pygame.font.Font(FONT_PATH, 28)
        self.smallfont = pygame.font.Font(FONT_PATH, 20)
        self.asr = PathummaASR()
        self.rec = Recorder(SAMPLE_RATE, CHANNELS, MAX_SPEAK_SECONDS)
        self.fields = {
            "prompt": TextField(pygame.Rect(120, 150, 560, 50), self.font, "พิมพ์สิ่งที่อยากพูดหรือหัวข้อซ้อม..."),
            "expect": TextField(pygame.Rect(120, 220, 560, 50), self.font, "ตัวอย่างคำตอบที่ถือว่าถูกต้อง (คั่นด้วย ,)"),
        }
        self.send_button = Button(pygame.Rect(120, 290, 240, 50), "คุยกับคนท้องถิ่น 🤝", ORANGE, WHITE)
        self.feedback = None
        self.recording = False
        self.dialect = self.game.state.get("dialect", DIALECTS[0])
        self.game.state["dialect"] = self.dialect
        self.dialect_rects = []
        for idx, key in enumerate(DIALECTS):
            rect = pygame.Rect(120 + idx * 150, 90, 140, 44)
            self.dialect_rects.append((key, rect))
        self.conversation = []
        self.ai_thinking = False
        self.ai_error: str | None = None
        self.max_messages = 6

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return "EXIT"
                for f in self.fields.values(): f.handle(e)
                if e.type == pygame.MOUSEBUTTONDOWN:
                    if self.send_button.rect.collidepoint(e.pos):
                        self._trigger_ai()
                    for key, rect in self.dialect_rects:
                        if rect.collidepoint(e.pos):
                            self.dialect = key
                            self.game.state["dialect"] = key
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE: return "MENU"
                    if e.key == pygame.K_m:
                        if not self.recording:
                            self.rec.start(); self.recording = True
                        else:
                            wav = self.rec.stop_to_wav()
                            self.recording = False
                            text = self.asr.transcribe(wav)
                            targets = [
                                t.strip()
                                for t in self.fields["expect"].text.split(",")
                                if t.strip()
                            ]
                            if targets:
                                best = max(fuzz.partial_ratio(text, t) for t in targets)
                            else:
                                best = 0
                            self.feedback = (text, best)
                    if e.key == pygame.K_RETURN and self.fields["prompt"].focus:
                        self._trigger_ai()
                    if pygame.K_F1 <= e.key <= pygame.K_F4:
                        idx = e.key - pygame.K_F1
                        if 0 <= idx < len(DIALECTS):
                            self.dialect = DIALECTS[idx]
                            self.game.state["dialect"] = self.dialect

            self.screen.fill(WHITE)

            title = self.font.render("โหมดพูดอิสระ", True, BLACK)
            self.screen.blit(title, (120, 40))
            subtitle = self.smallfont.render("กด M เพื่ออัดเสียง · Enter เพื่อคุยกับคนท้องถิ่น", True, (90, 90, 90))
            self.screen.blit(subtitle, (120, 70))

            # Dialect chips
            for key, rect in self.dialect_rects:
                selected = key == self.dialect
                color = GREEN if selected else WHITE
                border_color = GREEN
                pygame.draw.rect(self.screen, color, rect, border_radius=20)
                pygame.draw.rect(self.screen, border_color, rect, width=2, border_radius=20)
                label = self.smallfont.render(DIALECT_LABELS.get(key, key), True, WHITE if selected else GREEN)
                self.screen.blit(label, label.get_rect(center=rect.center))

            for f in self.fields.values():
                f.draw(self.screen)
            self.send_button.draw(self.screen, self.font, hovered=self.send_button.rect.collidepoint(pygame.mouse.get_pos()))

            status_y = 360
            convo_rect = pygame.Rect(120, status_y, 560, 180)
            pygame.draw.rect(self.screen, GRAY, convo_rect, border_radius=18)
            pygame.draw.rect(self.screen, BLUE, convo_rect, width=2, border_radius=18)

            msg_y = convo_rect.y + 16
            for speaker, message in self.conversation[-self.max_messages:]:
                wrapped = textwrap.wrap(message, width=40) or [message]
                speaker_prefix = f"{speaker}: "
                first_line = wrapped[0]
                lines = [speaker_prefix + first_line] + ["   " + line for line in wrapped[1:]]
                for line in lines:
                    txt = self.smallfont.render(line, True, BLACK)
                    self.screen.blit(txt, (convo_rect.x + 16, msg_y))
                    msg_y += txt.get_height() + 4
                    if msg_y > convo_rect.bottom - 20:
                        break
                if msg_y > convo_rect.bottom - 20:
                    break

            if self.ai_thinking:
                thinking = self.smallfont.render("🤖 คนท้องถิ่นกำลังคิดคำตอบ...", True, BLUE)
                self.screen.blit(thinking, (self.send_button.rect.right + 20, self.send_button.rect.y + 10))
            elif self.ai_error:
                err_txt = self.smallfont.render(f"⚠️ {self.ai_error}", True, RED)
                self.screen.blit(err_txt, (self.send_button.rect.right + 20, self.send_button.rect.y + 10))

            if self.recording:
                recording_txt = self.smallfont.render("● กำลังบันทึกเสียง...", True, RED)
                self.screen.blit(recording_txt, (120, convo_rect.bottom + 20))
            elif self.feedback:
                spoken, score = self.feedback
                fb_text = self.smallfont.render(f"คุณพูดว่า: {spoken}  (คะแนน {score:.1f})", True, GREEN)
                self.screen.blit(fb_text, (120, convo_rect.bottom + 20))

            pygame.display.flip()
            clock.tick(FPS)

    def _trigger_ai(self):
        message = self.fields["prompt"].text.strip()
        if not message:
            self.ai_error = "พิมพ์ข้อความก่อนโต้ตอบ"
            return
        self.ai_error = None
        history = self.conversation[-self.max_messages :]
        self.conversation.append(("คุณ", message))
        self.fields["prompt"].text = ""
        self.ai_thinking = True
        pygame.display.flip()
        pygame.event.pump()
        try:
            reply = roleplay_response(message, self.dialect, history)
        except Exception as exc:
            self.ai_error = str(exc)
        else:
            speaker_name = f"ชาว{DIALECT_LABELS.get(self.dialect, self.dialect)}"
            self.conversation.append((speaker_name, reply))
        finally:
            self.ai_thinking = False
            if len(self.conversation) > self.max_messages:
                self.conversation = self.conversation[-self.max_messages :]
