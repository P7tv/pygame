import os
import pygame, random, time, math
from core.ui import HeaderUI, ProgressBar, Button, Card, PRIMARY, SECONDARY, ACCENT, LIGHT_TEXT, DARK_BG, WHITE, BLACK
from core.sound_manager import SoundManager
from config import *
from core.data_loader import category_path, load_lessons, save_lessons
from core.audio import Recorder, PathummaASR
from rapidfuzz import fuzz
from ai.llm_gen import generate_lessons


class LessonScene:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen

        # Fonts
        self.header_font = pygame.font.Font(FONT_PATH, 48)
        self.prompt_font = pygame.font.Font(FONT_PATH, 52)
        self.target_font = pygame.font.Font(FONT_PATH, 32)
        self.label_font = pygame.font.Font(FONT_PATH, 28)
        self.small_font = pygame.font.Font(FONT_PATH, 24)

        self.mode = self.game.state.get("mode", "standard")
        self.challenge_level = self.game.state.get("challenge_level", DEFAULT_CHALLENGE_LEVEL)
        self.category_key = self.game.state.get("category", DEFAULT_CATEGORY_KEY)
        self.category_label = next((c["label"] for c in CONTENT_CATEGORIES if c["key"] == self.category_key), self.category_key)

        self.cards = []
        self.generation_error = None
        self._load_cards()

        self.index = 0
        self.asr = PathummaASR()  # manager that uses worker process
        # Ask the worker to start loading model in background
        self.asr.start_loading()
        self.rec = Recorder(SAMPLE_RATE, CHANNELS, MAX_SPEAK_SECONDS)
        self.recording = False
        self.feedback = None
        self.feedback_time = 0
        self.hearts = 3
        self.xp = 0
        self.streak = self.game.state.get("streak", 0)
        self.dialect = self.game.state.get("dialect", DIALECTS[0])
        self.game.state["dialect"] = self.dialect
        self.game.dialect = self.dialect

        if not self.cards:
            raise RuntimeError("ไม่พบบทเรียนที่ใช้งานได้")

        self.header = HeaderUI(self.xp, self.streak, self.hearts, self.dialect, self.index, len(self.cards))

        # Flags for non-blocking transcription
        self.waiting_transcription_job = None
        self._last_wav_path = None
        self.processing_audio = False

    def _load_cards(self):
        """Load cards from challenge or standard mode"""
        if self.mode == "challenge":
            self._load_challenge_cards()
        else:
            self._load_standard_cards()
        self.cards = list(self.cards)
        random.shuffle(self.cards)

    def _load_standard_cards(self):
        """Load standard lesson cards"""
        cat_file = category_path(self.category_key)
        try:
            if not os.path.exists(cat_file):
                generated = generate_lessons(self.category_key, LESSON_COUNT)
                save_lessons(cat_file, generated)
                self.cards = list(generated)
                return
        except Exception as exc:
            self.generation_error = str(exc)

        if not self.cards:
            try:
                self.cards, _ = load_lessons(category_key=self.category_key, preferred=cat_file)
            except FileNotFoundError as exc:
                raise RuntimeError("ไม่พบข้อมูลบทเรียน") from exc

    def _load_challenge_cards(self):
        """Load challenge mode cards"""
        level_cfg = CHALLENGE_LEVELS.get(self.challenge_level, CHALLENGE_LEVELS[DEFAULT_CHALLENGE_LEVEL])
        mix = self.game.state.get("challenge_mix")
        if not mix:
            available = [c["key"] for c in CONTENT_CATEGORIES]
            random.shuffle(available)
            mix = available[:level_cfg["category_mix"]]
            self.game.state["challenge_mix"] = mix

        cards = []
        for key in mix:
            try:
                lessons, _ = load_lessons(category_key=key, preferred=category_path(key))
                random.shuffle(lessons)
                cards.extend(lessons)
            except FileNotFoundError:
                continue

        if not cards:
            raise RuntimeError("ไม่พบบทเรียนสำหรับโหมดชาเลนจ์")

        random.shuffle(cards)
        self.cards = cards[:level_cfg["rounds"]]

    def evaluate(self, text, targets):
        """Evaluate transcribed text against target answers"""
        best = max(fuzz.partial_ratio(text, t) for t in targets) if targets else 0
        if best >= ASR_THRESHOLD_OK:
            return "ok", best
        return "partial" if best >= ASR_THRESHOLD_PARTIAL else "bad", best

    def run(self):
        self.record_button = Button(
            pygame.Rect(WIDTH // 2 - 200, HEIGHT - 200, 400, 120),
            "🎙️ บันทึกเสียง",
            PRIMARY,
            WHITE,
            radius=60
        )

        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return "EXIT"
                if e.type == pygame.VIDEORESIZE:
                    self.game.handle_resize(e)
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        return "MENU"
                    if e.key == pygame.K_m:
                        if self._is_asr_ready():
                            self._toggle_recording()

                pointer = self.game.logical_pos(e.pos) if hasattr(e, "pos") else None
                # no hover SFX for record button (clicks play sounds in handlers)

                if e.type == pygame.MOUSEBUTTONDOWN and pointer:
                    if self.record_button.rect.collidepoint(pointer) and self._is_asr_ready():
                        self._toggle_recording()

            self.screen.fill(WHITE)
            # Poll for background transcription result (non-blocking)
            if self.waiting_transcription_job is not None:
                status, text = self.asr.get_result(self.waiting_transcription_job)
                if status != "pending":
                    # clear pending flag
                    self.waiting_transcription_job = None
                    if status == "ok":
                        self._handle_transcription_result(text)
                    else:
                        # transcription failed; log and treat as bad attempt (empty text)
                        print(f"[Lesson] transcription job {self.waiting_transcription_job} error: {text}")
                        self._handle_transcription_result("")

            self._draw_ui()
            self.game.present()

    def _toggle_recording(self):
        """Toggle recording on/off"""
        if not self.recording:
            self.rec.start()
            self.recording = True
        else:
            # Stop recording: perform WAV write and transcription request in a background thread
            self.recording = False
            self._last_wav_path = None
            self.processing_audio = True

            def _stop_and_request():
                try:
                    wav = self.rec.stop_to_wav()
                    self._last_wav_path = wav
                    job_id = self.asr.request_transcribe(wav)
                    self.waiting_transcription_job = job_id
                except Exception as exc:
                    print(f"[Lesson] background stop/request failed: {exc}")
                finally:
                    # finished handing off
                    try:
                        self.processing_audio = False
                    except Exception:
                        pass

            import threading as _thr
            t = _thr.Thread(target=_stop_and_request, daemon=True)
            t.start()

    def _handle_transcription_result(self, text):
        """Handle transcription result (called after background transcribe finishes)"""
        targets = self.cards[self.index]["targets"].get(self.dialect, [])
        kind, score = self.evaluate(text, targets)
        self.feedback = (kind, score, text)
        self.feedback_time = time.time()

        # Play sound based on result
        sound_mgr = SoundManager()
        if kind == "ok":
            self.xp += 10
            self.streak += 1
            sound_mgr.play_ok()
        elif kind == "partial":
            self.xp += 5
            sound_mgr.play_ok()
        else:
            self.hearts -= 1
            self.streak = 0
            sound_mgr.play_bad()

        self.game.state.update({"xp": self.xp, "streak": self.streak, "hearts": self.hearts})
        self.index += 1

        if self.index >= len(self.cards) or self.hearts <= 0:
            self.game.state.update({"streak": self.streak, "xp": self.xp})
            if self.mode == "challenge":
                for key in ("mode", "challenge_level", "challenge_mix"):
                    self.game.state.pop(key, None)

    def _draw_ui(self):
        """Draw the lesson UI in Duolingo style"""
        self.header.update(self.xp, self.streak, self.hearts, self.dialect, self.index, len(self.cards))
        self.header.draw(self.screen)
        # ASR status indicator (top-right)
        status = self.asr.get_status()
        ready = self._is_asr_ready(status)
        small = pygame.font.Font(FONT_PATH, 18)
        status_txt = small.render(f"ASR: {status}", True, LIGHT_TEXT)
        status_r = status_txt.get_rect()
        status_r.topright = (WIDTH - 20, 30)
        pygame.draw.rect(self.screen, WHITE, (status_r.x - 8, status_r.y - 6, status_r.w + 16, status_r.h + 12), border_radius=8)
        pygame.draw.rect(self.screen, (220,220,220), (status_r.x - 8, status_r.y - 6, status_r.w + 16, status_r.h + 12), 1, border_radius=8)
        self.screen.blit(status_txt, status_r)

        if self.generation_error:
            err_txt = self.label_font.render(f"⚠️ {self.generation_error}", True, (200, 50, 50))
            self.screen.blit(err_txt, (100, 200))
            return

        # Check if lesson complete
        if self.index >= len(self.cards) or self.hearts <= 0:
            self._draw_completion()
            return

        card = self.cards[self.index]

        # White card with shadow
        card_rect = pygame.Rect(200, 180, WIDTH - 400, 500)
        pygame.draw.rect(self.screen, (240, 240, 240), card_rect.move(0, 8), border_radius=30)
        pygame.draw.rect(self.screen, WHITE, card_rect, border_radius=30)
        pygame.draw.rect(self.screen, (220, 220, 220), card_rect, 2, border_radius=30)

        # Category label
        cat_txt = self.label_font.render(self.category_label, True, LIGHT_TEXT)
        self.screen.blit(cat_txt, (card_rect.x + 40, card_rect.y + 30))

        # Prompt (main question)
        prompt = self.prompt_font.render(card["prompt"], True, (20, 20, 20))
        self.screen.blit(prompt, (card_rect.x + 40, card_rect.y + 90))

        # Target answers
        targets = card["targets"].get(self.dialect, [])
        y_offset = card_rect.y + 280
        target_label = self.label_font.render("เป้าหมายการตอบ:", True, LIGHT_TEXT)
        self.screen.blit(target_label, (card_rect.x + 40, y_offset))

        for i, answer in enumerate(targets[:3]):
            answer_rect = pygame.Rect(card_rect.x + 40, y_offset + 50 + i * 50, card_rect.width - 80, 45)
            pygame.draw.rect(self.screen, (240, 245, 250), answer_rect, border_radius=12)
            pygame.draw.rect(self.screen, SECONDARY, answer_rect, 2, border_radius=12)
            ans_txt = self.target_font.render(f"✓ {answer}", True, SECONDARY)
            self.screen.blit(ans_txt, (answer_rect.x + 20, answer_rect.y + 8))

        # Recording button or loading status
        mouse_pos = self.game.mouse_pos()
        if not ready:
            # Loading indicator
            loading_rect = pygame.Rect(card_rect.x + 40, HEIGHT - 200, card_rect.width - 80, 100)
            pygame.draw.rect(self.screen, (255, 245, 200), loading_rect, border_radius=20)
            pygame.draw.rect(self.screen, SECONDARY, loading_rect, 3, border_radius=20)
            loading_txt = self.label_font.render(f"⏳ สถานะ ASR: {status}", True, (100, 80, 0))
            self.screen.blit(loading_txt, (loading_rect.x + 30, loading_rect.y + 35))
        else:
            # Recording button with state
            if self.recording:
                blink = int(abs(math.sin(time.time() * 5)) * 80 + 150)
                self.record_button.bg = (255, blink, blink)
                self.record_button.label = "⏹️ หยุดบันทึก"
            else:
                self.record_button.bg = PRIMARY
                self.record_button.label = "🎙️ บันทึกเสียง"

            self.record_button.draw(self.screen, self.label_font, hovered=self.record_button.collide(mouse_pos))
            # Processing overlay while WAV is being written / transcription requested
            if getattr(self, 'processing_audio', False):
                proc_rect = pygame.Rect(card_rect.centerx - 200, card_rect.bottom - 140, 400, 60)
                pygame.draw.rect(self.screen, (255, 255, 255), proc_rect, border_radius=12)
                pygame.draw.rect(self.screen, (220, 220, 220), proc_rect, 2, border_radius=12)
                small = pygame.font.Font(FONT_PATH, 20)
                tick = (pygame.time.get_ticks() // 300) % 4
                dots = '.' * tick
                txt = small.render(f"กำลังประมวลผลเสียง{dots}", True, (40, 40, 40))
                self.screen.blit(txt, (proc_rect.x + 20, proc_rect.y + 14))

        # Feedback overlay
        if self.feedback and time.time() - self.feedback_time < 4:
            self._draw_feedback()

    def _draw_feedback(self):
        """Draw feedback message after recording"""
        kind, score, text = self.feedback

        # Feedback colors and messages
        fb_config = {
            "ok": (PRIMARY, WHITE, "✅ ยอดเยี่ยม! +10 XP", "สอบผ่านแล้ว!"),
            "partial": ((255, 200, 50), WHITE, "⚠️ ใกล้แล้ว! +5 XP", "ตัวอักษรถูก แต่เสียงต้องชัดขึ้น"),
            "bad": ((255, 100, 100), WHITE, "❌ ลองใหม่ -1❤️", "ยังไม่ตรงกัน ลองใหม่นะ")
        }
        color, text_color, msg, detail = fb_config.get(kind, (SECONDARY, WHITE, "?", ""))

        # Feedback panel
        fb_rect = pygame.Rect(200, HEIGHT - 350, WIDTH - 400, 120)
        pygame.draw.rect(self.screen, color, fb_rect, border_radius=20)
        pygame.draw.rect(self.screen, text_color, fb_rect, 3, border_radius=20)

        # Message
        msg_txt = self.label_font.render(msg, True, text_color)
        self.screen.blit(msg_txt, (fb_rect.x + 40, fb_rect.y + 15))

        # Detail and spoken text
        detail_txt = self.small_font.render(detail, True, text_color)
        self.screen.blit(detail_txt, (fb_rect.x + 40, fb_rect.y + 55))

        spoken_txt = self.small_font.render(f"คุณพูด: '{text}'", True, text_color)
        self.screen.blit(spoken_txt, (fb_rect.x + 40, fb_rect.y + 85))

        # Simple success accent (star) when OK
        if kind == "ok":
            elapsed = time.time() - self.feedback_time
            pulse = int(1 + (math.sin(elapsed * 6) + 1) * 6)
            star_txt = self.label_font.render("✨", True, WHITE)
            star_pos = (fb_rect.right - 80, fb_rect.y + fb_rect.height // 2 - 16 - pulse)
            self.screen.blit(star_txt, star_pos)

    def _draw_completion(self):
        """Draw lesson completion screen"""
        # Celebration background
        self.screen.fill((240, 250, 255))

        # Center message
        msg_rect = pygame.Rect(200, HEIGHT // 2 - 150, WIDTH - 400, 300)
        pygame.draw.rect(self.screen, WHITE, msg_rect, border_radius=40)
        pygame.draw.rect(self.screen, PRIMARY, msg_rect, 4, border_radius=40)

        if self.hearts <= 0:
            title = self.prompt_font.render("เวลาหมดแล้ว!", True, (200, 50, 50))
            detail = self.label_font.render(f"ได้ {self.xp} XP จากรอบนี้", True, LIGHT_TEXT)
        else:
            title = self.prompt_font.render("🎉 สอบผ่านแล้ว!", True, PRIMARY)
            detail = self.label_font.render(f"ได้ {self.xp} XP • {self.streak} 🔥 streak", True, LIGHT_TEXT)

        self.screen.blit(title, (msg_rect.x + 50, msg_rect.y + 60))
        self.screen.blit(detail, (msg_rect.x + 50, msg_rect.y + 150))

        # Back button
        back_btn = Button(
            pygame.Rect(msg_rect.x + 50, msg_rect.y + 240, msg_rect.width - 100, 50),
            "← กลับไปเมนู",
            SECONDARY,
            WHITE,
            radius=25
        )

        mouse_pos = self.game.mouse_pos()
        back_btn.draw(self.screen, self.label_font, hovered=back_btn.collide(mouse_pos))

    def _is_asr_ready(self, status=None):
        """Return True when ASR model is ready for another recording"""
        status = status if status is not None else self.asr.get_status()
        return status in {"loaded", "done"}
