import pygame, time, textwrap
from core.ui import TextField, Button, Card, PRIMARY, SECONDARY, ACCENT, LIGHT_TEXT, DARK_BG, WHITE, BLACK
from core.audio import Recorder, PathummaASR
from rapidfuzz import fuzz
from config import *
from ai.dialect_advisor import roleplay_response


class FreeSpeakScene:
    """โหมดสนทนาอิสระ: ผู้เล่นพิมพ์หรือพูดเพื่อคุยกับ AI ตามสำเนียงที่เลือก"""

    def __init__(self, game):
        self.game = game
        self.screen = game.screen

        # ฟอนต์หลายขนาดสำหรับหัวเรื่อง, รายละเอียด, และข้อความในประวัติแชท
        self.title_font = pygame.font.Font(FONT_PATH, 64)
        self.header_font = pygame.font.Font(FONT_PATH, 48)
        self.label_font = pygame.font.Font(FONT_PATH, 28)
        self.font = pygame.font.Font(FONT_PATH, 26)
        self.small_font = pygame.font.Font(FONT_PATH, 20)

        self.asr = PathummaASR()
        # เริ่มโหลดโมเดลพูด-เป็น-ข้อความตั้งแต่เข้าฉากเพื่อรอทันทีเมื่อผู้เล่นกด
        self.asr.start_loading()
        self.rec = Recorder(SAMPLE_RATE, CHANNELS, MAX_SPEAK_SECONDS)
        self.waiting_transcription_job = None
        self.processing_audio = False

        # สร้างปุ่มเลือกสำเนียง 4 ปุ่มวางกลางจอ
        self.dialect_buttons = []
        btn_width = 140
        btn_height = 50
        btn_gap = 16
        total_w = btn_width * 4 + btn_gap * 3
        start_x = (WIDTH - total_w) // 2

        colors = [PRIMARY, ACCENT, SECONDARY, (200, 50, 100)]
        for i, (d, color) in enumerate(zip(DIALECTS, colors)):
            btn = Button(
                pygame.Rect(start_x + i * (btn_width + btn_gap), 160, btn_width, btn_height),
                DIALECT_LABELS[d],
                color, WHITE, radius=10
            )
            self.dialect_buttons.append((d, btn))

        # กล่องข้อความให้ผู้เล่นพิมพ์หัวข้อ/คำถามก่อนเริ่มคุย
        self.prompt_field = TextField(
            pygame.Rect(200, 280, WIDTH - 400, 60),
            self.font,
            "พูดหัวข้อการสนทนา เช่น 'สวัสดี' หรือ 'คุณชื่ออะไร'..."
        )

        self.send_button = Button(
            pygame.Rect(WIDTH // 2 - 150, 380, 300, 70),
            "เริ่มสนทนา 🎤",
            PRIMARY,
            WHITE,
            radius=35
        )

        self.feedback = None
        self.recording = False
        self.dialect = self.game.state.get("dialect", DIALECTS[0])
        self.game.state["dialect"] = self.dialect

        # เก็บประวัติสนทนาและสถานะสำหรับแจ้งกำลังโหลด/เกิดข้อผิดพลาด
        self.conversation = []
        self.ai_thinking = False
        self.ai_error = None

    def run(self):
        """ลูปหลักของฉาก: รับ event, ควบคุมการบันทึก และอัปเดตข้อความ AI"""
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return "EXIT"
                if e.type == pygame.VIDEORESIZE:
                    self.game.handle_resize(e)
                if e.type == pygame.KEYDOWN:
                    # ปุ่มลัด: ESC กลับเมนู, M เริ่ม/หยุดอัดเสียง, Enter ส่งข้อความ
                    if e.key == pygame.K_ESCAPE:
                        return "MENU"
                    if e.key == pygame.K_m:
                        if self.asr.get_status() == "loaded":
                            self._toggle_recording()
                    if e.key == pygame.K_RETURN and self.prompt_field.focus:
                        self._send_message()

                pointer = self.game.logical_pos(e.pos) if hasattr(e, "pos") else None  # ตำแหน่งเมาส์บน canvas
                if e.type == pygame.MOUSEBUTTONDOWN and pointer:
                    # ปรับสำเนียงที่อยากคุย (บันทึกลง state เพื่อให้ AI ใช้)
                    for d, btn in self.dialect_buttons:
                        if btn.collide(pointer):
                            self.dialect = d
                            self.game.state["dialect"] = d

                    if self.send_button.collide(pointer):
                        self._send_message()

                self.prompt_field.handle(e, pointer_pos=pointer)

            # ตรวจสอบงานถอดเสียงที่ค้างอยู่
            if self.waiting_transcription_job is not None:
                # ตรวจสอบผลลัพธ์ที่ worker ส่งกลับ หากเสร็จแล้วเติมข้อความลง TextField
                status, txt = self.asr.get_result(self.waiting_transcription_job)
                if status != "pending":
                    self.waiting_transcription_job = None
                    if status == "ok":
                        self.prompt_field.text = txt
                    else:
                        # เก็บข้อความ error ไว้โชว์ให้ผู้ใช้
                        self.ai_error = f"ASR error: {txt}"

            self.screen.fill(WHITE)
            self._draw_ui()
            self.game.present()

    def _toggle_recording(self):
        """เริ่ม/หยุดบันทึกเสียง แล้วคิวงานให้ ASR ถอดข้อความ"""
        if not self.recording:
            self.rec.start()
            self.recording = True
        else:
            # หยุดแล้วให้ thread แยกจัดการบันทึกไฟล์และยิงคำขอถอดเสียง
            self.recording = False
            self.processing_audio = True

            def _stop_and_request():
                try:
                    wav = self.rec.stop_to_wav()
                    job = self.asr.request_transcribe(wav)
                    self.waiting_transcription_job = job
                except Exception as exc:
                    print(f"[FreeSpeak] background stop/request failed: {exc}")
                finally:
                    try:
                        self.processing_audio = False
                    except Exception:
                        pass

            import threading as _thr
            t = _thr.Thread(target=_stop_and_request, daemon=True)
            t.start()

    def _send_message(self):
        """รวบรวมประโยคของผู้ใช้ ส่งให้ LLM roleplay แล้วอัปเดตประวัติ"""
        msg = self.prompt_field.text.strip()
        if not msg:
            self.ai_error = "พิมพ์ข้อความก่อน"
            return

        self.ai_error = None
        self.conversation.append(("คุณ", msg))
        self.prompt_field.text = ""
        self.ai_thinking = True
        self.game.present()
        pygame.event.pump()

        try:
            reply = roleplay_response(msg, self.dialect, self.conversation[-6:])
            speaker = f"ชาว{DIALECT_LABELS.get(self.dialect, self.dialect)}"
            self.conversation.append((speaker, reply))
            self.conversation = self.conversation[-12:]
        except Exception as exc:
            self.ai_error = str(exc)
        finally:
            self.ai_thinking = False

    def _draw_ui(self):
        """วาด UI โหมดพูดอิสระ: ส่วนหัว, ปุ่มเลือกสำเนียง, กล่องแชท"""
        # ส่วนหัว
        pygame.draw.rect(self.screen, DARK_BG, (0, 0, WIDTH, 120))
        pygame.draw.line(self.screen, (220, 220, 220), (0, 119), (WIDTH, 119), 1)

        title = self.title_font.render("🎤 พูดอิสระ", True, (40, 40, 40))
        self.screen.blit(title, (50, 25))

        # ป้ายเลือกสำเนียง
        dialect_label = self.label_font.render("เลือกสำเนียง", True, LIGHT_TEXT)
        self.screen.blit(dialect_label, (50, 150))

        # ปุ่มสำเนียง
        mouse_pos = self.game.mouse_pos()
        for d, btn in self.dialect_buttons:
            btn.draw(self.screen, self.label_font, hovered=btn.collide(mouse_pos))

        # ช่องหัวข้อสนทนา
        prompt_label = self.label_font.render("หัวข้อการสนทนา", True, LIGHT_TEXT)
        self.screen.blit(prompt_label, (200, 250))
        self.prompt_field.draw(self.screen)

        # ปุ่มเริ่มสนทนา/ส่งข้อความ
        self.send_button.draw(self.screen, self.label_font, hovered=self.send_button.collide(mouse_pos))

        # กล่องแชท
        conv_rect = pygame.Rect(200, 500, WIDTH - 400, 550)
        pygame.draw.rect(self.screen, (240, 245, 250), conv_rect, border_radius=20)
        pygame.draw.rect(self.screen, (220, 220, 220), conv_rect, 2, border_radius=20)

        # พิมพ์ข้อความโต้ตอบจากประวัติ
        msg_y = conv_rect.y + 20
        for speaker, message in self.conversation[-10:]:
            wrapped = textwrap.wrap(message, width=60)
            prefix = f"👤 {speaker}: " if speaker == "คุณ" else f"🗣️ {speaker}: "

            for i, line in enumerate(wrapped):
                txt_line = (prefix + line) if i == 0 else ("  " + line)
                txt_color = PRIMARY if speaker == "คุณ" else SECONDARY
                txt = self.small_font.render(txt_line, True, txt_color)
                self.screen.blit(txt, (conv_rect.x + 20, msg_y))
                msg_y += txt.get_height() + 6

                if msg_y > conv_rect.bottom - 40:
                    break

            msg_y += 5
            if msg_y > conv_rect.bottom - 40:
                break

        # แถบสถานะด้านล่างช่วยให้ผู้ใช้รู้ว่าระบบกำลังทำอะไร
        status_y = HEIGHT - 100
        if self.ai_thinking:
            thinking = self.font.render("🤖 AI กำลังตัวสนทนา...", True, SECONDARY)
            self.screen.blit(thinking, (200, status_y))
        elif self.ai_error:
            err = self.font.render(f"⚠️ {self.ai_error}", True, (200, 50, 50))
            self.screen.blit(err, (200, status_y))
        elif self.recording:
            rec = self.font.render("● บันทึกเสียง...", True, (255, 100, 100))
            self.screen.blit(rec, (200, status_y))
        elif getattr(self, 'processing_audio', False):
            proc = self.font.render("กำลังประมวลผลเสียง...", True, (40, 40, 40))
            self.screen.blit(proc, (200, status_y))
        else:
            hint = self.small_font.render("กด M เพื่อบันทึกเสียง | Esc เพื่อกลับเมนู", True, LIGHT_TEXT)
            self.screen.blit(hint, (200, status_y))
