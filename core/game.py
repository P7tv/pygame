import pygame, sys
from config import *


class Game:
    """คลาสกลางที่ถือสถานะเกมและหมุนเวียน scene ต่าง ๆ"""

    def __init__(self, scenes, initial_scene="MENU"):
        pygame.init()
        pygame.display.set_caption("🦉 Learn Thai Dialects")
        self.base_size = (WIDTH, HEIGHT)
        # สร้างหน้าต่างหลักแบบปรับขนาดได้พร้อม Surface สำหรับวาด
        self.display = pygame.display.set_mode(self.base_size, pygame.RESIZABLE)
        self.canvas = pygame.Surface(self.base_size, pygame.SRCALPHA).convert_alpha()
        self.screen = self.canvas
        self.clock = pygame.time.Clock()
        self.running = True
        self.current_scene = None
        self.scene_map = scenes  # ผังชื่อ scene ไปยังคลาสที่ต้องการสร้าง
        # สถานะกลางที่แชร์ระหว่างแต่ละฉาก เช่น สะสม XP หรือหมวดที่เลือก
        self.state = {
            "xp": 0,
            "streak": 0,
            "best_streak": 0,
            "hearts": 3,
            "dialect": DIALECTS[0],
            "category": DEFAULT_CATEGORY_KEY,
            "challenge_unlocked": DEFAULT_CHALLENGE_UNLOCK.copy(),
            "challenge_completed": {key: False for key in CHALLENGE_LEVEL_ORDER},
        }
        self.dialect = self.state["dialect"]
        self.category = self.state["category"]
        start = initial_scene if initial_scene in self.scene_map else "MENU"
        self.switch_scene(start)

    def _scale_factor(self):
        """คำนวณสัดส่วนระหว่างหน้าต่างจริงกับ canvas base สำหรับปรับตำแหน่งเมาส์"""
        win_w, win_h = self.display.get_size()
        return (WIDTH / win_w if win_w else 1, HEIGHT / win_h if win_h else 1)

    def logical_pos(self, pos):
        """แปลงพิกัดเมาส์ของหน้าต่างจริงให้กลายเป็นพิกัดบน canvas"""
        sx, sy = self._scale_factor()
        return (int(pos[0] * sx), int(pos[1] * sy))

    def mouse_pos(self):
        """อ่านพิกัดเมาส์ปัจจุบันในหน่วย canvas"""
        return self.logical_pos(pygame.mouse.get_pos())

    def switch_scene(self, name):
        """เปลี่ยนไป scene ใหม่ตามชื่อที่ map ไว้"""
        scene_class = self.scene_map.get(name)
        if scene_class:
            self.current_scene = scene_class(self)
            self.current_scene_name = name

    def handle_resize(self, event):
        """ปรับขนาดหน้าต่างเมื่อผู้ใช้ย่อ-ขยาย โดยบังคับขั้นต่ำเพื่อให้ UI ไม่เพี้ยน"""
        new_size = (max(event.w, 800), max(event.h, 600))
        self.display = pygame.display.set_mode(new_size, pygame.RESIZABLE)

    def present(self):
        """เรนเดอร์ canvas ลงหน้าต่างจริง (scale ถ้าจำเป็น) แล้ว flip เฟรม"""
        window_size = self.display.get_size()
        if window_size == self.base_size:
            self.display.blit(self.canvas, (0, 0))
        else:
            scaled = pygame.transform.smoothscale(self.canvas, window_size)
            self.display.blit(scaled, (0, 0))
        pygame.display.flip()

    def run(self):
        """ลูปหลัก: ส่งสิทธิ์การควบคุมไปยัง scene ปัจจุบันและรอผลตอบกลับ"""
        while self.running:
            result = self.current_scene.run()
            if result in self.scene_map:
                # ถ้า scene คืนชื่อฉากถัดไป -> ย้ายฉากตามนั้น
                self.switch_scene(result)
            elif result == "EXIT":
                self.running = False
        pygame.quit()
        sys.exit()
