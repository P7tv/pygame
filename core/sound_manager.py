import pygame
from config import SOUND_OK, SOUND_BAD


class SoundManager:
    """จัดการเสียงเอฟเฟกต์ทั้งหมดของเกมแบบ singleton"""
    _instance = None
    _lock = None

    def __new__(cls):
        """สร้างอินสแตนซ์เดียวและเก็บไว้ในคลาส"""
        if cls._instance is None:
            if cls._lock is None:
                cls._lock = object()
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """เริ่ม pygame mixer และโหลดไฟล์เสียงหากยังไม่ได้ทำ"""
        if self._initialized:
            return

        pygame.mixer.init()
        self.sounds = {}
        self._load_sounds()
        self._initialized = True

    def _load_sounds(self):
        """โหลดไฟล์เสียงทั้งหมดแล้วตั้งระดับความดัง"""
        try:
            self.sounds['ok'] = pygame.mixer.Sound(SOUND_OK)
            self.sounds['ok'].set_volume(0.7)
        except Exception as e:
            print(f"[Sound] Failed to load ok.wav: {e}")
            self.sounds['ok'] = None

        try:
            self.sounds['bad'] = pygame.mixer.Sound(SOUND_BAD)
            self.sounds['bad'].set_volume(0.7)
        except Exception as e:
            print(f"[Sound] Failed to load bad.wav: {e}")
            self.sounds['bad'] = None
        # เสียงคลิกเบา ๆ: ใช้ไฟล์ ok เดิมแต่ลดความดัง
        try:
            self.sounds['click'] = pygame.mixer.Sound(SOUND_OK) if self.sounds.get('ok') is not None else None
            if self.sounds['click']:
                self.sounds['click'].set_volume(0.25)
        except Exception:
            self.sounds['click'] = None

    def play(self, sound_name):
        """สั่งเล่นเสียงตามชื่อ ถ้าโหลดสำเร็จ"""
        if sound_name not in self.sounds:
            return False

        sound = self.sounds[sound_name]
        if sound is None:
            return False

        try:
            sound.play()
            return True
        except Exception as e:
            print(f"[Sound] Failed to play {sound_name}: {e}")
            return False

    def play_ok(self):
        """เสียงเมื่อตอบถูกหรือกดปุ่มสำคัญ"""
        return self.play('ok')

    def play_bad(self):
        """เสียงเตือนเวลาตอบผิด"""
        return self.play('bad')

    def play_click(self):
        """เสียงคลิกเบา ๆ ใช้กับ hover/เลือกปุ่ม"""
        return self.play('click')
