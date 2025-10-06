# game.py
# Duolingo Dialect — Speak Only (ใช้ PathummaASR) + Free Speak Mode
import os, sys, time, random, math
import pygame
from dataclasses import dataclass
from rapidfuzz import fuzz

from config import *
from asr import Recorder, PathummaASR
from lessons import DEFAULT_LESSONS, load_json

# ---------------------------
# UI helpers
# ---------------------------
@dataclass
class Button:
    rect: pygame.Rect
    label: str
    bg: tuple
    fg: tuple
    radius: int = 16
    hover_scale: float = 1.02
    shadow: bool = True

    def draw(self, surf, font, hovered=False):
        r = self.rect
        if hovered:
            scaled = pygame.Rect(0, 0, int(r.w * self.hover_scale), int(r.h * self.hover_scale))
            scaled.center = r.center
            # Shadow
            if self.shadow:
                shadow_rect = scaled.copy()
                shadow_rect.y += 4
                pygame.draw.rect(surf, (0, 0, 0, 40), shadow_rect, border_radius=self.radius)
            # Button
            color = tuple(min(255, int(c * 1.1)) for c in self.bg)
            pygame.draw.rect(surf, color, scaled, border_radius=self.radius)
        else:
            # Shadow
            if self.shadow:
                shadow_rect = r.copy()
                shadow_rect.y += 3
                pygame.draw.rect(surf, (0, 0, 0, 30), shadow_rect, border_radius=self.radius)
            # Button
            pygame.draw.rect(surf, self.bg, r, border_radius=self.radius)
        
        txt = font.render(self.label, True, self.fg)
        surf.blit(txt, txt.get_rect(center=r.center))

class TextField:
    def __init__(self, rect, font, placeholder="", text="", maxlen=120):
        self.rect = rect
        self.font = font
        self.placeholder = placeholder
        self.text = text
        self.focus = False
        self.maxlen = maxlen

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.focus = self.rect.collidepoint(event.pos)
        if self.focus and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return "submit"
            elif event.unicode and len(self.text) < self.maxlen:
                self.text += event.unicode
        return None

    def draw(self, surf):
        bg_color = (255, 255, 255) if self.focus else (245, 247, 250)
        border_color = (88, 204, 2) if self.focus else (220, 225, 230)
        border_width = 3 if self.focus else 2
        
        pygame.draw.rect(surf, bg_color, self.rect, border_radius=12)
        pygame.draw.rect(surf, border_color, self.rect, width=border_width, border_radius=12)
        
        show = self.text if (self.text or self.focus) else self.placeholder
        color = (45, 55, 72) if (self.text or self.focus) else (160, 174, 192)
        surf.blit(self.font.render(show, True, color), (self.rect.x+16, self.rect.y+12))

class AnimatedProgress:
    def __init__(self):
        self.current = 0.0
        self.target = 0.0
        
    def set_target(self, value):
        self.target = value
        
    def update(self):
        if abs(self.target - self.current) > 0.001:
            self.current += (self.target - self.current) * 0.15
        else:
            self.current = self.target
            
    def get(self):
        return self.current

# ---------------------------
# Game
# ---------------------------
class Game:
    def __init__(self, lessons=None):
        pygame.init()
        pygame.display.setcaption = pygame.display.set_caption
        pygame.display.setcaption("🦉 Duolingo Thai Dialects")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        if FONT_PATH and os.path.exists(FONT_PATH):
            self.font      = pygame.font.Font(FONT_PATH, 26)
            self.font_big  = pygame.font.Font(FONT_PATH, 42)
            self.font_small= pygame.font.Font(FONT_PATH, 20)
            self.font_title= pygame.font.Font(FONT_PATH, 56)
        else:
            try:
                self.font      = pygame.font.SysFont("Tahoma", 26)
                self.font_big  = pygame.font.SysFont("Tahoma", 42)
                self.font_small= pygame.font.SysFont("Tahoma", 20)
                self.font_title= pygame.font.SysFont("Tahoma", 56)
            except:
                self.font      = pygame.font.Font(None, 26)
                self.font_big  = pygame.font.Font(None, 42)
                self.font_small= pygame.font.Font(None, 20)
                self.font_title= pygame.font.Font(None, 56)

        self.state = {"xp":0, "streak":0, "best_streak":0}
        self.cards = list(lessons or DEFAULT_LESSONS)
        random.shuffle(self.cards)
        self.index = 0
        self.correct = 0
        self.hearts = 3
        self.feedback = None  # (kind, score, tgt, ts)

        # sounds (optional)
        self.snd_ok = self._load_sound("assets/ok.wav")
        self.snd_bad = self._load_sound("assets/bad.wav")

        # ASR (Pathumma)
        self.asr = PathummaASR(device="cpu")  # เปลี่ยนเป็น "cuda" หากมี GPU
        self.rec = Recorder(SAMPLE_RATE, CHANNELS, MAX_SPEAK_SECONDS)
        self.asr_busy = False
        self.recording = False
        self.asr_last_text = ""

        # dialect + scene
        self.dialect = "central"
        self.scene = "MENU"

        # free speak state
        self.fs_prompt = ""
        self.fs_expect = ""  # comma-separated expected phrases
        self.fs_fields = None
        self.fs_feedback = None  # (kind, score, tgt, ts)
        
        self.progress_anim = AnimatedProgress()
        self.pulse_time = 0

    # ---------- utils ----------
    def _load_sound(self, path):
        try:
            if path and os.path.exists(path):
                pygame.mixer.init()
                return pygame.mixer.Sound(path)
        except Exception:
            pass
        return None

    def draw_header(self):
        # Gradient background for header
        header_height = 80
        for y in range(header_height):
            alpha = 1 - (y / header_height) * 0.3
            color = tuple(int(c * alpha) for c in (255, 255, 255))
            pygame.draw.line(self.screen, color, (0, y), (WIDTH, y))
        
        # Bottom border
        pygame.draw.line(self.screen, (220, 225, 230), (0, header_height), (WIDTH, header_height), 2)
        
        # Left side - XP with icon
        xp_x = 24
        pygame.draw.circle(self.screen, (255, 204, 0), (xp_x + 16, 40), 18)
        xp_surf = self.font_small.render(f"{self.state['xp']}", True, (45, 55, 72))
        self.screen.blit(xp_surf, (xp_x + 40, 30))
        
        # Streak with fire emoji effect
        streak_x = 140
        if self.state['streak'] > 0:
            # Animated fire color
            fire_color = (255, 140 + int(20 * math.sin(self.pulse_time * 3)), 0)
            pygame.draw.circle(self.screen, fire_color, (streak_x + 16, 40), 18)
        else:
            pygame.draw.circle(self.screen, (200, 200, 200), (streak_x + 16, 40), 18)
        streak_surf = self.font_small.render(f"{self.state['streak']}", True, (45, 55, 72))
        self.screen.blit(streak_surf, (streak_x + 40, 30))
        
        # Hearts with better styling
        heart_x = 260
        for i in range(3):
            x_pos = heart_x + i * 32
            if i < self.hearts:
                # Full heart - red with gradient effect
                pygame.draw.circle(self.screen, (255, 75, 75), (x_pos, 40), 14)
                pygame.draw.circle(self.screen, (255, 120, 120), (x_pos - 2, 38), 6)
            else:
                # Empty heart - gray outline
                pygame.draw.circle(self.screen, (220, 225, 230), (x_pos, 40), 14, 3)
        
        # Dialect selector - right side with flag-like colors
        dialect_colors = {
            "central": (88, 204, 2),
            "northern": (28, 176, 246),
            "isan": (255, 159, 67),
            "southern": (206, 93, 174)
        }
        dlabel = DIALECT_LABELS.get(self.dialect, self.dialect)
        dialect_bg = dialect_colors.get(self.dialect, (88, 204, 2))
        
        dialect_rect = pygame.Rect(WIDTH - 200, 25, 180, 36)
        pygame.draw.rect(self.screen, dialect_bg, dialect_rect, border_radius=18)
        d_surf = self.font_small.render(f"🗣️ {dlabel}", True, (255, 255, 255))
        self.screen.blit(d_surf, d_surf.get_rect(center=dialect_rect.center))
        
        # Progress bar for lessons (if not in menu or free mode)
        if self.scene not in ["MENU", "FREE"]:
            prog = (self.index) / max(1, len(self.cards))
            self.progress_anim.set_target(prog)
            self.progress_anim.update()
            
            bar_y = header_height + 8
            bar_height = 8
            bar_width = WIDTH - 48
            bar_x = 24
            
            # Background
            pygame.draw.rect(self.screen, (229, 234, 242), 
                           (bar_x, bar_y, bar_width, bar_height), border_radius=4)
            # Progress with gradient
            prog_width = int(bar_width * self.progress_anim.get())
            if prog_width > 0:
                pygame.draw.rect(self.screen, (88, 204, 2), 
                               (bar_x, bar_y, prog_width, bar_height), border_radius=4)

    def normalize_dialect(self, text):
        t = (text or "").strip()
        mp = NORMALIZE_MAP.get(self.dialect, {})
        for k, v in mp.items():
            t = t.replace(k, v)
        return t

    def evaluate(self, text, targets):
        base = self.normalize_dialect(text).lower()
        best = -1
        best_target = ""
        for t in targets:
            s = fuzz.partial_ratio(base, t.lower())
            if s > best:
                best = s; best_target = t
        if best >= ASR_THRESHOLD_OK:
            return "ok", best, best_target
        elif best >= ASR_THRESHOLD_PARTIAL:
            return "partial", best, best_target
        else:
            return "bad", best, best_target

    def draw_card(self, card_data):
        prompt = card_data["prompt"]
        
        # Main card with shadow
        card = pygame.Rect(60, 120, WIDTH - 120, HEIGHT - 240)
        shadow = card.copy()
        shadow.y += 6
        pygame.draw.rect(self.screen, (0, 0, 0, 20), shadow, border_radius=24)
        pygame.draw.rect(self.screen, (255, 255, 255), card, border_radius=24)
        
        # Top section with colored accent
        accent_rect = pygame.Rect(card.x, card.y, card.w, 80)
        pygame.draw.rect(self.screen, (249, 250, 251), accent_rect, border_top_left_radius=24, border_top_right_radius=24)
        
        # Prompt text with icon
        icon_y = card.y + 28
        pygame.draw.circle(self.screen, (88, 204, 2), (card.x + 40, icon_y), 20)
        title = self.font_big.render(prompt, True, (45, 55, 72))
        self.screen.blit(title, (card.x + 75, card.y + 18))
        
        # Divider line
        pygame.draw.line(self.screen, (229, 234, 242), 
                        (card.x + 24, card.y + 80), 
                        (card.right - 24, card.y + 80), 2)
        
        # Examples section with better styling
        targets = card_data.get("targets", {}).get(self.dialect) or card_data.get("targets", {}).get("central", [])
        
        label_y = card.y + 110
        label = self.font_small.render("ตัวอย่างคำตอบ:", True, (107, 114, 128))
        self.screen.blit(label, (card.x + 32, label_y))
        
        # Example chips
        chip_y = label_y + 35
        chip_x = card.x + 32
        for target in targets[:3]:  # Show max 3 examples
            chip_surf = self.font.render(target, True, (45, 55, 72))
            chip_w = chip_surf.get_width() + 32
            chip_rect = pygame.Rect(chip_x, chip_y, chip_w, 40)
            pygame.draw.rect(self.screen, (243, 244, 246), chip_rect, border_radius=20)
            pygame.draw.rect(self.screen, (209, 213, 219), chip_rect, width=2, border_radius=20)
            self.screen.blit(chip_surf, (chip_x + 16, chip_y + 8))
            chip_x += chip_w + 12
        
        # Recording status with animated indicator
        status_y = card.y + 220
        if self.recording:
            # Animated recording indicator
            pulse = int(10 * math.sin(self.pulse_time * 8))
            rec_size = 16 + pulse
            pygame.draw.circle(self.screen, (239, 68, 68), (card.x + 40, status_y), rec_size)
            rec_text = self.font.render("กำลังบันทึกเสียง...", True, (239, 68, 68))
            self.screen.blit(rec_text, (card.x + 65, status_y - 12))
        elif self.asr_busy:
            # Processing indicator
            pygame.draw.circle(self.screen, (251, 191, 36), (card.x + 40, status_y), 14)
            proc_text = self.font.render("กำลังประมวลผล...", True, (251, 191, 36))
            self.screen.blit(proc_text, (card.x + 65, status_y - 12))
        else:
            # Ready to record
            pygame.draw.circle(self.screen, (88, 204, 2), (card.x + 40, status_y), 14)
            ready_text = self.font_small.render("กด M เพื่อบันทึกเสียง", True, (107, 114, 128))
            self.screen.blit(ready_text, (card.x + 65, status_y - 10))
        
        # What we heard
        if self.asr_last_text:
            heard_y = status_y + 50
            heard_label = self.font_small.render("คุณพูดว่า:", True, (107, 114, 128))
            self.screen.blit(heard_label, (card.x + 32, heard_y))
            heard_text = self.font.render(f'"{self.asr_last_text}"', True, (88, 204, 2))
            self.screen.blit(heard_text, (card.x + 32, heard_y + 30))

    def draw_free(self):
        # Main card
        card = pygame.Rect(60, 120, WIDTH - 120, HEIGHT - 240)
        shadow = card.copy()
        shadow.y += 6
        pygame.draw.rect(self.screen, (0, 0, 0, 20), shadow, border_radius=24)
        pygame.draw.rect(self.screen, (255, 255, 255), card, border_radius=24)
        
        # Header section
        header_rect = pygame.Rect(card.x, card.y, card.w, 80)
        pygame.draw.rect(self.screen, (249, 250, 251), header_rect, border_top_left_radius=24, border_top_right_radius=24)
        
        # Title with icon
        pygame.draw.circle(self.screen, (28, 176, 246), (card.x + 40, card.y + 40), 20)
        title = self.font_big.render("โหมดพูดอิสระ", True, (45, 55, 72))
        self.screen.blit(title, (card.x + 75, card.y + 22))

        if self.fs_fields is None:
            self.fs_fields = {
                "prompt": TextField(pygame.Rect(card.x+32, card.y+110, card.w-64, 50), self.font_small,
                                   placeholder="พิมพ์คำสั่ง เช่น: พูดคำทักทายแบบอีสาน"),
                "expect": TextField(pygame.Rect(card.x+32, card.y+180, card.w-64, 50), self.font_small,
                                   placeholder="คำตอบที่ถูก เช่น: แซบหลาย, สวัสดีเด้อ"),
            }
        
        # Draw fields with labels
        prompt_label = self.font_small.render("คำสั่ง:", True, (107, 114, 128))
        self.screen.blit(prompt_label, (card.x + 32, card.y + 90))
        self.fs_fields["prompt"].draw(self.screen)
        
        expect_label = self.font_small.render("คำตอบที่ถูกต้อง:", True, (107, 114, 128))
        self.screen.blit(expect_label, (card.x + 32, card.y + 160))
        self.fs_fields["expect"].draw(self.screen)

        # Recording status
        status_y = card.y + 260
        if self.recording:
            pulse = int(10 * math.sin(self.pulse_time * 8))
            rec_size = 16 + pulse
            pygame.draw.circle(self.screen, (239, 68, 68), (card.x + 40, status_y), rec_size)
            rec_text = self.font.render("กำลังบันทึกเสียง...", True, (239, 68, 68))
            self.screen.blit(rec_text, (card.x + 65, status_y - 12))
        elif self.asr_busy:
            pygame.draw.circle(self.screen, (251, 191, 36), (card.x + 40, status_y), 14)
            proc_text = self.font.render("กำลังประมวลผล...", True, (251, 191, 36))
            self.screen.blit(proc_text, (card.x + 65, status_y - 12))
        else:
            pygame.draw.circle(self.screen, (88, 204, 2), (card.x + 40, status_y), 14)
            ready_text = self.font_small.render("กด M เพื่อบันทึก | Enter ยืนยัน | ESC กลับ", True, (107, 114, 128))
            self.screen.blit(ready_text, (card.x + 65, status_y - 10))

        # What we heard
        if self.asr_last_text:
            heard_y = status_y + 50
            heard_label = self.font_small.render("คุณพูดว่า:", True, (107, 114, 128))
            self.screen.blit(heard_label, (card.x + 32, heard_y))
            heard_text = self.font.render(f'"{self.asr_last_text}"', True, (88, 204, 2))
            self.screen.blit(heard_text, (card.x + 32, heard_y + 30))

        # Feedback
        if self.fs_feedback:
            kind, score, tgt, ts = self.fs_feedback
            feedback_y = card.bottom - 80
            
            if kind == "ok":
                color = (88, 204, 2)
                msg = "✓ ยอดเยี่ยม!"
            elif kind == "partial":
                color = (251, 191, 36)
                msg = "~ ใกล้แล้ว!"
            else:
                color = (239, 68, 68)
                msg = "✗ ลองใหม่!"
            
            msg += f" (คะแนน {int(score)})"
            ftxt = self.font.render(msg, True, color)
            self.screen.blit(ftxt, ftxt.get_rect(center=(card.centerx, feedback_y)))

    # ---------- scenes ----------
    def run_menu(self):
        while True:
            self.pulse_time += 0.016  # For animations
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit(0)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if start_rect.collidepoint(event.pos):
                        self.scene = "LESSON"; return
                    if free_rect.collidepoint(event.pos):
                        self.scene = "FREE"; return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F1: self.dialect = "central"
                    if event.key == pygame.K_F2: self.dialect = "northern"
                    if event.key == pygame.K_F3: self.dialect = "isan"
                    if event.key == pygame.K_F4: self.dialect = "southern"

            # Gradient background
            for y in range(HEIGHT):
                ratio = y / HEIGHT
                r = int(240 + (255 - 240) * ratio)
                g = int(248 + (255 - 248) * ratio)
                b = int(255)
                self.screen.fill((r, g, b), (0, y, WIDTH, 1))
            
            self.draw_header()
            
            # Owl mascot placeholder (circle)
            owl_y = 180
            pygame.draw.circle(self.screen, (88, 204, 2), (WIDTH//2, owl_y), 50)
            pygame.draw.circle(self.screen, (255, 255, 255), (WIDTH//2 - 15, owl_y - 10), 12)
            pygame.draw.circle(self.screen, (255, 255, 255), (WIDTH//2 + 15, owl_y - 10), 12)
            pygame.draw.circle(self.screen, (45, 55, 72), (WIDTH//2 - 15, owl_y - 10), 6)
            pygame.draw.circle(self.screen, (45, 55, 72), (WIDTH//2 + 15, owl_y - 10), 6)
            
            # Title
            title = self.font_title.render("ภาษาถิ่นไทย", True, (45, 55, 72))
            self.screen.blit(title, title.get_rect(center=(WIDTH//2, 270)))
            
            subtitle = self.font.render("เรียนรู้สำเนียงท้องถิ่นด้วยการพูด", True, (107, 114, 128))
            self.screen.blit(subtitle, subtitle.get_rect(center=(WIDTH//2, 320)))

            # Buttons with new styling
            start_rect = pygame.Rect(0,0,320,70)
            start_rect.center = (WIDTH//2, HEIGHT - 160)
            free_rect  = pygame.Rect(0,0,320,70)
            free_rect.center  = (WIDTH//2, HEIGHT - 75)

            start_btn = Button(start_rect, "เริ่มบทเรียน ▶", (88, 204, 2), (255, 255, 255), radius=35)
            free_btn  = Button(free_rect , "โหมดพูดอิสระ 🎤", (28, 176, 246), (255, 255, 255), radius=35)

            start_btn.draw(self.screen, self.font_big, hovered=start_rect.collidepoint(pygame.mouse.get_pos()))
            free_btn.draw(self.screen, self.font, hovered=free_rect.collidepoint(pygame.mouse.get_pos()))
            
            # Dialect hint
            hint = self.font_small.render("เลือกสำเนียง: F1 กลาง | F2 เหนือ | F3 อีสาน | F4 ใต้", True, (160, 174, 192))
            self.screen.blit(hint, hint.get_rect(center=(WIDTH//2, HEIGHT - 25)))

            pygame.display.flip()
            self.clock.tick(FPS)

    def run_lesson(self):
        while True:
            self.pulse_time += 0.016
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit(0)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "MENU"
                    if event.key == pygame.K_m and not self.asr_busy:
                        if not self.recording:
                            try:
                                self.rec.start(); self.recording = True; self.asr_last_text = ""
                            except Exception as e:
                                print("Record error:", e); self.recording = False
                        else:
                            self.recording = False
                            wav = self.rec.stop_to_wav()
                            self.asr_busy = True
                            def worker(card, dialect, path):
                                text = ""
                                try:
                                    text = self.asr.transcribe(path)
                                except Exception as e:
                                    print("ASR error:", e)
                                self.asr_last_text = text
                                targets = card.get("targets", {}).get(dialect) or card.get("targets", {}).get("central", [])
                                kind, score, tgt = self.evaluate(text, targets)
                                if kind == "ok":
                                    self.correct += 1
                                    if self.snd_ok: self.snd_ok.play()
                                elif kind == "bad":
                                    self.hearts -= 1
                                    if self.snd_bad: self.snd_bad.play()
                                self.feedback = (kind, score, tgt, time.time())
                                self.asr_busy = False
                                try: os.unlink(path)
                                except Exception: pass
                            import threading
                            threading.Thread(target=worker, args=(self.cards[self.index], self.dialect, wav), daemon=True).start()
                    if event.key == pygame.K_F1: self.dialect = "central"
                    if event.key == pygame.K_F2: self.dialect = "northern"
                    if event.key == pygame.K_F3: self.dialect = "isan"
                    if event.key == pygame.K_F4: self.dialect = "southern"

            # Gradient background
            for y in range(HEIGHT):
                ratio = y / HEIGHT
                r = int(240 + (255 - 240) * ratio)
                g = int(248 + (255 - 248) * ratio)
                b = int(255)
                self.screen.fill((r, g, b), (0, y, WIDTH, 1))
            
            self.draw_header()
            card = self.cards[self.index]
            self.draw_card(card)

            if self.feedback:
                kind, score, tgt, ts = self.feedback
                feedback_y = HEIGHT - 100
                
                # Animated feedback badge
                if kind == "ok":
                    color = (88, 204, 2)
                    bg_color = (220, 252, 231)
                    msg = "✓ ยอดเยี่ยม!"
                elif kind == "partial":
                    color = (251, 191, 36)
                    bg_color = (254, 243, 199)
                    msg = "~ ใกล้แล้ว!"
                else:
                    color = (239, 68, 68)
                    bg_color = (254, 226, 226)
                    msg = "✗ ลองอีกครั้ง!"
                
                msg += f" (คะแนน {int(score)})"
                
                # Badge background
                badge_rect = pygame.Rect(0, 0, 400, 60)
                badge_rect.center = (WIDTH//2, feedback_y)
                pygame.draw.rect(self.screen, bg_color, badge_rect, border_radius=30)
                pygame.draw.rect(self.screen, color, badge_rect, width=3, border_radius=30)
                
                ftxt = self.font_big.render(msg, True, color)
                self.screen.blit(ftxt, ftxt.get_rect(center=badge_rect.center))

                if time.time() - ts > 2.5:
                    self.index += 1
                    self.feedback = None
                    if self.hearts <= 0 or self.index >= len(self.cards):
                        return "SUMMARY"

            pygame.display.flip()
            self.clock.tick(FPS)

    def run_free(self):
        self.asr_last_text = ""
        self.fs_feedback = None
        if self.fs_fields:
            self.fs_fields["prompt"].text = self.fs_fields["prompt"].text.strip()
            self.fs_fields["expect"].text = self.fs_fields["expect"].text.strip()

        while True:
            self.pulse_time += 0.016
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit(0)
                if self.fs_fields:
                    for name, field in self.fs_fields.items():
                        res = field.handle(event)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "MENU"
                    if event.key == pygame.K_m and not self.asr_busy:
                        if not self.recording:
                            try:
                                self.rec.start(); self.recording = True; self.asr_last_text = ""
                            except Exception as e:
                                print("Record error:", e); self.recording = False
                        else:
                            self.recording = False
                            wav = self.rec.stop_to_wav()
                            self.asr_busy = True
                            expects = []
                            if self.fs_fields and self.fs_fields["expect"].text.strip():
                                expects = [x.strip() for x in self.fs_fields["expect"].text.split(",") if x.strip()]
                            if not expects:
                                expects = [""]
                            def worker(path, expects_list):
                                text = ""
                                try:
                                    text = self.asr.transcribe(path)
                                except Exception as e:
                                    print("ASR error:", e)
                                self.asr_last_text = text
                                kind, score, tgt = self.evaluate(text, expects_list)
                                self.fs_feedback = (kind, score, tgt, time.time())
                                self.asr_busy = False
                                try: os.unlink(path)
                                except Exception: pass
                            import threading
                            threading.Thread(target=worker, args=(wav, expects), daemon=True).start()
            
            # Gradient background
            for y in range(HEIGHT):
                ratio = y / HEIGHT
                r = int(240 + (255 - 240) * ratio)
                g = int(248 + (255 - 248) * ratio)
                b = int(255)
                self.screen.fill((r, g, b), (0, y, WIDTH, 1))
            
            self.draw_header()
            self.draw_free()
            pygame.display.flip()
            self.clock.tick(FPS)

    def run_summary(self):
        finished = self.index >= len(self.cards)
        gained = max(0, (self.correct * 12) - (3 - self.hearts) * 6)
        if finished and self.hearts > 0 and self.correct > 0:
            self.state["streak"] += 1
        else:
            self.state["streak"] = 0
        self.state["best_streak"] = max(self.state["best_streak"], self.state["streak"])
        self.state["xp"] += gained

        while True:
            self.pulse_time += 0.016
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit(0)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if again_rect.collidepoint(event.pos):
                        self.index = 0
                        self.correct = 0
                        self.hearts = 3
                        random.shuffle(self.cards)
                        return "LESSON"
                    if menu_rect.collidepoint(event.pos):
                        self.index = 0
                        self.correct = 0
                        self.hearts = 3
                        return "MENU"

            # Gradient background
            for y in range(HEIGHT):
                ratio = y / HEIGHT
                r = int(240 + (255 - 240) * ratio)
                g = int(248 + (255 - 248) * ratio)
                b = int(255)
                self.screen.fill((r, g, b), (0, y, WIDTH, 1))
            
            self.draw_header()
            
            # Results card
            card = pygame.Rect(100, 140, WIDTH - 200, HEIGHT - 280)
            shadow = card.copy()
            shadow.y += 6
            pygame.draw.rect(self.screen, (0, 0, 0, 20), shadow, border_radius=24)
            pygame.draw.rect(self.screen, (255, 255, 255), card, border_radius=24)
            
            # Success/failure indicator
            if self.hearts > 0 and finished:
                # Success
                pygame.draw.circle(self.screen, (88, 204, 2), (WIDTH//2, card.y + 60), 40)
                icon = self.font_title.render("✓", True, (255, 255, 255))
                self.screen.blit(icon, icon.get_rect(center=(WIDTH//2, card.y + 60)))
                title = self.font_big.render("เยี่ยมมาก!", True, (45, 55, 72))
            else:
                # Try again
                pygame.draw.circle(self.screen, (251, 191, 36), (WIDTH//2, card.y + 60), 40)
                icon = self.font_title.render("!", True, (255, 255, 255))
                self.screen.blit(icon, icon.get_rect(center=(WIDTH//2, card.y + 60)))
                title = self.font_big.render("ลองใหม่อีกครั้ง", True, (45, 55, 72))
            
            self.screen.blit(title, title.get_rect(center=(WIDTH//2, card.y + 130)))
            
            # Stats
            stats_y = card.y + 190
            score_text = self.font.render(f"ผ่าน {self.correct} / {len(self.cards)} ข้อ", True, (107, 114, 128))
            self.screen.blit(score_text, score_text.get_rect(center=(WIDTH//2, stats_y)))
            
            xp_text = self.font_big.render(f"+{gained} XP", True, (88, 204, 2))
            self.screen.blit(xp_text, xp_text.get_rect(center=(WIDTH//2, stats_y + 50)))

            # Buttons
            again_rect = pygame.Rect(0,0,280,64)
            again_rect.center = (WIDTH//2, card.bottom - 100)
            again_btn = Button(again_rect, "ทำอีกครั้ง", (88, 204, 2), (255, 255, 255), radius=32)
            again_btn.draw(self.screen, self.font_big, hovered=again_rect.collidepoint(pygame.mouse.get_pos()))

            menu_rect = pygame.Rect(0,0,200,50)
            menu_rect.center = (WIDTH//2, card.bottom - 30)
            menu_btn = Button(menu_rect, "กลับเมนู", (229, 234, 242), (107, 114, 128), radius=25, shadow=False)
            menu_btn.draw(self.screen, self.font, hovered=menu_rect.collidepoint(pygame.mouse.get_pos()))

            pygame.display.flip()
            self.clock.tick(FPS)

    def run(self):
        while True:
            self.run_menu()
            if self.scene == "LESSON":
                res = self.run_lesson()
                if res == "MENU":
                    self.scene = "MENU"; continue
                if res == "SUMMARY":
                    self.scene = "SUMMARY"
            if self.scene == "SUMMARY":
                res = self.run_summary()
                self.scene = res
            if self.scene == "FREE":
                res = self.run_free()
                self.scene = res

# ---------------------------
# Entrypoint
# ---------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--load", type=str, help="ไฟล์บทเรียน JSON ที่เตรียมไว้ (optional)")
    parser.add_argument("--gen", type=str, help="หัวข้อให้ LLM สร้างบทพูด (optional)")
    parser.add_argument("--n", type=int, default=8)
    parser.add_argument("--out", type=str, default="generated_lessons.json")
    parser.add_argument("--use", action="store_true")
    args = parser.parse_args()

    lessons_loaded = None

    if args.gen:
        try:
            import llm_gen, lessons as L
            data = llm_gen.generate(args.gen, args.n)
            L.save_json(args.out, data)
            print(f"[LLM] saved to {args.out}")
            if args.use:
                lessons_loaded = data
        except Exception as e:
            print("[LLM] generation failed:", e)

    if (not lessons_loaded) and args.load and os.path.exists(args.load):
        lessons_loaded = load_json(args.load)

    Game(lessons=lessons_loaded).run()
