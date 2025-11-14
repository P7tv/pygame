import pygame
from config import SOUND_OK, SOUND_BAD

class SoundManager:
    """Manages sound effects throughout the game"""
    _instance = None
    _lock = None
    
    def __new__(cls):
        if cls._instance is None:
            if cls._lock is None:
                cls._lock = object()
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        pygame.mixer.init()
        self.sounds = {}
        self._load_sounds()
        self._initialized = True
    
    def _load_sounds(self):
        """Load all sound effects"""
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
        # small click sound: reuse ok.wav at lower volume if present
        try:
            self.sounds['click'] = pygame.mixer.Sound(SOUND_OK) if self.sounds.get('ok') is not None else None
            if self.sounds['click']:
                self.sounds['click'].set_volume(0.25)
        except Exception:
            self.sounds['click'] = None
    
    def play(self, sound_name):
        """Play a sound effect"""
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
        """Play success sound"""
        return self.play('ok')
    
    def play_bad(self):
        """Play failure sound"""
        return self.play('bad')

    def play_click(self):
        """Play click/hover sound (low volume)"""
        return self.play('click')
