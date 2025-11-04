import pygame, time
from core.ui import TextField
from core.audio import Recorder, PathummaASR
from rapidfuzz import fuzz
from config import *

class FreeSpeakScene:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.font = pygame.font.Font(FONT_PATH, 28)
        self.asr = PathummaASR()
        self.rec = Recorder(SAMPLE_RATE, CHANNELS, MAX_SPEAK_SECONDS)
        self.fields = {
            "prompt": TextField(pygame.Rect(120, 150, 560, 50), self.font, "พิมพ์สิ่งที่อยากพูด..."),
            "expect": TextField(pygame.Rect(120, 230, 560, 50), self.font, "ตัวอย่างคำตอบถูกต้อง..."),
        }
        self.feedback = None
        self.recording = False

    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT: return "EXIT"
                for f in self.fields.values(): f.handle(e)
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE: return "MENU"
                    if e.key == pygame.K_m:
                        if not self.recording:
                            self.rec.start(); self.recording = True
                        else:
                            wav = self.rec.stop_to_wav()
                            self.recording = False
                            text = self.asr.transcribe(wav)
                            targets = self.fields["expect"].text.split(",")
                            best = max(fuzz.partial_ratio(text, t) for t in targets)
                            self.feedback = (text, best)

            self.screen.fill(WHITE)
            for f in self.fields.values(): f.draw(self.screen)
            if self.feedback:
                fb = self.font.render(f"{self.feedback[0]} ({self.feedback[1]:.1f})", True, GREEN)
                self.screen.blit(fb, (120, 320))
            pygame.display.flip()
