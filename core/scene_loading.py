import time
import pygame

from config import WIDTH, HEIGHT, FONT_PATH, WHITE, FPS
from core.ui import PRIMARY, SECONDARY, DARK_BG
from core.audio import PathummaASR


class LoadingScene:
    """ฉากโหลดแรกเข้า: รอให้โมเดล ASR พร้อมก่อนเข้าเมนู"""

    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.title_font = pygame.font.Font(FONT_PATH, 54)
        self.body_font = pygame.font.Font(FONT_PATH, 28)
        self.status_font = pygame.font.Font(FONT_PATH, 22)
        self.asr = PathummaASR()
        self.asr.start_loading()
        self.ready_since: float | None = None
        self.error_message: str | None = None

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return "EXIT"
                if e.type == pygame.VIDEORESIZE:
                    self.game.handle_resize(e)

            status = self.asr.get_status()
            if status.startswith("error"):
                self.error_message = status
            elif status == "loaded":
                if self.ready_since is None:
                    self.ready_since = time.time()
                elif time.time() - self.ready_since > 0.8:
                    return "MENU"
            else:
                self.ready_since = None

            self._draw(status)
            self.game.present()
            clock.tick(FPS)

    def _draw(self, status: str):
        self.screen.fill(DARK_BG)

        title = self.title_font.render("กำลังเตรียมระบบเสียง", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80)))

        body = self.body_font.render("รอสักครู่ โมเดลรู้จำเสียงกำลังโหลด...", True, WHITE)
        self.screen.blit(body, body.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))

        # วาดวงกลมหมุนๆ เป็น indicator
        center = (WIDTH // 2, HEIGHT // 2 + 80)
        radius = 40
        pygame.draw.circle(self.screen, (65, 75, 85), center, radius, width=6)
        angle = (pygame.time.get_ticks() // 4) % 360
        vec = pygame.Vector2(radius, 0).rotate(angle)
        indicator_pos = (int(center[0] + vec.x), int(center[1] + vec.y))
        pygame.draw.circle(self.screen, PRIMARY, indicator_pos, 10)

        status_text = f"สถานะ: {status}"
        status_surf = self.status_font.render(status_text, True, SECONDARY)
        self.screen.blit(status_surf, status_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 150)))

        if self.error_message:
            err = self.status_font.render(self.error_message, True, (255, 120, 120))
            self.screen.blit(err, err.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 200)))
