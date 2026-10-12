
import math
import random
from pathlib import Path

import pygame

# config---

WIDTH, HEIGHT = 800, 600
FPS = 60
ROAD_WIDTH = 440
ROAD_LEFT = (WIDTH - ROAD_WIDTH) // 2
ROAD_RIGHT = ROAD_LEFT + ROAD_WIDTH
LANE_COUNT = 4
LANE_WIDTH = ROAD_WIDTH // LANE_COUNT

WHITE = (245, 247, 250)
BLACK = (15, 18, 24)
DARK = (25, 29, 36)
ROAD_GRAY = (58, 62, 69)
ROAD_EDGE = (240, 190, 65)
GREEN = (30, 125, 70)
RED = (230, 65, 70)
BLUE = (55, 145, 245)
YELLOW = (250, 205, 60)
CYAN = (65, 220, 220)
PURPLE = (170, 105, 245)

BASE_DIR = Path(__file__).resolve().parent
HIGH_SCORE_FILE = BASE_DIR / "car_racing_highscore.txt"


def draw_text(surface, text, font, color, center):
    """Render centered text onto a surface."""
    image = font.render(str(text), True, color)
    surface.blit(image, image.get_rect(center=center))


def draw_car(surface, rect, body_color, player=False):
    """Draw a simple car sprite using shapes (no external image files needed)."""
    x, y, w, h = rect
    # Wheels
    wheel_color = (12, 13, 16)
    pygame.draw.rect(surface, wheel_color, (x - 4, y + 12, 8, 19), border_radius=3)
    pygame.draw.rect(surface, wheel_color, (x + w - 4, y + 12, 8, 19), border_radius=3)
    pygame.draw.rect(surface, wheel_color, (x - 4, y + h - 31, 8, 19), border_radius=3)
    pygame.draw.rect(surface, wheel_color, (x + w - 4, y + h - 31, 8, 19), border_radius=3)

    # Main body and bumpers
    pygame.draw.rect(surface, body_color, rect, border_radius=9)
    pygame.draw.rect(surface, tuple(max(0, c - 35) for c in body_color),
                     (x + 3, y + 8, w - 6, h - 16), width=2, border_radius=7)

    # Windshield and rear window
    glass = (150, 220, 235)
    pygame.draw.rect(surface, (25, 42, 55), (x + 7, y + 10, w - 14, 15), border_radius=4)
    pygame.draw.rect(surface, glass, (x + 8, y + 12, w - 16, 10), border_radius=3)
    pygame.draw.rect(surface, (25, 42, 55), (x + 7, y + h - 23, w - 14, 13), border_radius=4)

    # Racing stripe and lights
    if player:
        pygame.draw.rect(surface, WHITE, (x + w // 2 - 3, y + 28, 6, h - 39), border_radius=2)
    pygame.draw.rect(surface, (255, 245, 185), (x + 5, y + 3, 8, 4), border_radius=2)
    pygame.draw.rect(surface, (255, 245, 185), (x + w - 13, y + 3, 8, 4), border_radius=2)
    pygame.draw.rect(surface, (235, 50, 45), (x + 5, y + h - 6, 8, 4), border_radius=2)
    pygame.draw.rect(surface, (235, 50, 45), (x + w - 13, y + h - 6, 8, 4), border_radius=2)


class PlayerCar:
    """Player-controlled car with boundary-aware movement."""

    def __init__(self):
        self.width, self.height = 42, 72
        self.rect = pygame.Rect(WIDTH // 2 - self.width // 2,
                                HEIGHT - self.height - 35,
                                self.width, self.height)
        self.move_speed = 5.5

    def update(self, keys):
        dx = dy = 0
        if keys[pygame.K_LEFT]:
            dx -= self.move_speed
        if keys[pygame.K_RIGHT]:
            dx += self.move_speed
        if keys[pygame.K_UP]:
            dy -= self.move_speed
        if keys[pygame.K_DOWN]:
            dy += self.move_speed

        self.rect.x += round(dx)
        self.rect.y += round(dy)
        # Keep the whole car inside the road and screen play area.
        self.rect.left = max(ROAD_LEFT + 9, self.rect.left)
        self.rect.right = min(ROAD_RIGHT - 9, self.rect.right)
        self.rect.top = max(90, self.rect.top)
        self.rect.bottom = min(HEIGHT - 12, self.rect.bottom)

    def draw(self, surface):
        draw_car(surface, self.rect, BLUE, player=True)


class EnemyCar:
    """Enemy traffic car that travels down the road."""

    COLORS = [RED, YELLOW, PURPLE, (245, 125, 55), CYAN, (220, 90, 150)]

    def __init__(self, x, speed):
        self.width, self.height = 42, 72
        self.rect = pygame.Rect(x, -self.height - random.randint(0, 100),
                                self.width, self.height)
        self.speed = speed
        self.color = random.choice(self.COLORS)

    def update(self, speed_bonus):
        self.rect.y += round(self.speed + speed_bonus)

    def draw(self, surface):
        draw_car(surface, self.rect, self.color)


class Game:
    """Owns game state, menus, spawning, scoring, sound, and rendering."""

    DIFFICULTIES = {
        "Easy": {"base_speed": 3.0, "spawn_ms": 1050, "speed_gain": 0.12},
        "Medium": {"base_speed": 4.0, "spawn_ms": 820, "speed_gain": 0.18},
        "Hard": {"base_speed": 5.0, "spawn_ms": 650, "speed_gain": 0.24},
    }

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Neon Highway — Car Racing")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont("arial", 18, bold=True)
        self.font_medium = pygame.font.SysFont("arial", 27, bold=True)
        self.font_large = pygame.font.SysFont("arial", 48, bold=True)
        self.font_title = pygame.font.SysFont("arial", 54, bold=True)

        self.running = True
        self.state = "menu"
        self.difficulty_names = list(self.DIFFICULTIES)
        self.difficulty_index = 1
        self.difficulty = self.difficulty_names[self.difficulty_index]

        self.high_score = self.load_high_score()
        self.player = None
        self.enemies = []
        self.score = 0
        self.elapsed = 0.0
        self.road_offset = 0
        self.spawn_timer = 0
        self.crash_sound = self.make_crash_sound()
        self.music = self.make_background_music()
        self.music_playing = False

    # Pygame can synthesize a small crash noise without needing an external file.
    def make_crash_sound(self):
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            sample_rate = 22050
            duration = 0.32
            samples = int(sample_rate * duration)
            buffer = bytearray()
            for i in range(samples):
                t = i / sample_rate
                envelope = max(0.0, 1.0 - t / duration)
                noise = random.uniform(-1.0, 1.0)
                wave = (noise * 0.72 + math.sin(2 * math.pi * 95 * t) * 0.28)
                value = int(max(-1.0, min(1.0, wave * envelope)) * 12000)
                buffer.extend(int(value).to_bytes(2, byteorder="little", signed=True))
            return pygame.mixer.Sound(buffer=bytes(buffer))
        except (pygame.error, ValueError, OverflowError):
            return None

    def make_background_music(self):
        """Create a looping, synthesized racing pulse; no audio file is required."""
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            sample_rate = 22050
            duration = 1.2
            samples = int(sample_rate * duration)
            buffer = bytearray()
            notes = [110, 146.83, 164.81, 146.83]
            beat_samples = samples // len(notes)
            for i in range(samples):
                t = i / sample_rate
                note = notes[min(i // beat_samples, len(notes) - 1)]
                local_t = (i % beat_samples) / sample_rate
                envelope = min(1.0, local_t * 18) * max(0.0, 1.0 - local_t * 1.5)
                wave = math.sin(2 * math.pi * note * t) * 0.45
                wave += math.sin(2 * math.pi * note * 2 * t) * 0.15
                value = int(wave * envelope * 5000)
                buffer.extend(int(value).to_bytes(2, byteorder="little", signed=True))
            sound = pygame.mixer.Sound(buffer=bytes(buffer))
            sound.set_volume(0.22)
            return sound
        except (pygame.error, ValueError, OverflowError):
            return None

    def load_high_score(self):
        try:
            return max(0, int(HIGH_SCORE_FILE.read_text(encoding="utf-8").strip() or "0"))
        except (OSError, ValueError):
            return 0

    def save_high_score(self):
        try:
            HIGH_SCORE_FILE.write_text(str(self.high_score), encoding="utf-8")
        except OSError:
            pass  # The game can still be played if saving is not permitted.

    def start_music(self):
        if self.music and not self.music_playing:
            try:
                self.music.play(loops=-1)
                self.music_playing = True
            except pygame.error:
                pass

    def stop_music(self):
        if self.music:
            try:
                self.music.stop()
            except pygame.error:
                pass
        self.music_playing = False

    def start_game(self):
        self.player = PlayerCar()
        self.enemies = []
        self.score = 0
        self.elapsed = 0.0
        self.road_offset = 0
        self.spawn_timer = 0
        self.state = "playing"
        self.start_music()

    def game_over(self):
        self.state = "game_over"
        self.stop_music()
        if self.crash_sound:
            try:
                self.crash_sound.play()
            except pygame.error:
                pass
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == "menu":
                        self.running = False
                    else:
                        self.state = "menu"
                        self.stop_music()
                elif self.state == "menu":
                    if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        step = -1 if event.key == pygame.K_LEFT else 1
                        self.difficulty_index = (self.difficulty_index + step) % len(self.difficulty_names)
                        self.difficulty = self.difficulty_names[self.difficulty_index]
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.start_game()
                elif self.state == "playing":
                    if event.key == pygame.K_p:
                        self.state = "paused"
                        self.stop_music()
                elif self.state == "paused":
                    if event.key == pygame.K_p:
                        self.state = "playing"
                        self.start_music()
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.state = "playing"
                        self.start_music()
                elif self.state == "game_over":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.start_game()
                    elif event.key == pygame.K_m:
                        self.state = "menu"

    def update(self, dt):
        if self.state != "playing":
            return

        self.elapsed += dt
        self.score = int(self.elapsed * 10)
        config = self.DIFFICULTIES[self.difficulty]
        # Difficulty adds a different starting speed; survival increases it steadily.
        speed_bonus = self.elapsed * config["speed_gain"]
        world_speed = config["base_speed"] + speed_bonus
        self.road_offset = (self.road_offset + world_speed * 3.2) % 80

        self.spawn_timer += int(dt * 1000)
        spawn_interval = max(300, config["spawn_ms"] - int(self.elapsed * 7))
        if self.spawn_timer >= spawn_interval:
            self.spawn_timer = 0
            lane = random.randrange(LANE_COUNT)
            x = ROAD_LEFT + lane * LANE_WIDTH + (LANE_WIDTH - 42) // 2
            # Avoid stacking cars directly on top of each other at spawn time.
            if all(abs(enemy.rect.x - x) > 35 or enemy.rect.y > 100 for enemy in self.enemies):
                self.enemies.append(EnemyCar(x, world_speed * random.uniform(0.82, 1.08)))

        keys = pygame.key.get_pressed()
        self.player.update(keys)

        for enemy in self.enemies:
            enemy.update(speed_bonus)

        self.enemies = [enemy for enemy in self.enemies if enemy.rect.top < HEIGHT + 10]

        # Shrink hitboxes slightly to make collisions feel fair.
        player_hitbox = self.player.rect.inflate(-12, -12)
        for enemy in self.enemies:
            if player_hitbox.colliderect(enemy.rect.inflate(-10, -10)):
                self.game_over()
                break

    def draw_road(self):
        self.screen.fill(GREEN)
        pygame.draw.rect(self.screen, ROAD_GRAY, (ROAD_LEFT, 0, ROAD_WIDTH, HEIGHT))
        # Bright road edges
        pygame.draw.rect(self.screen, ROAD_EDGE, (ROAD_LEFT, 0, 6, HEIGHT))
        pygame.draw.rect(self.screen, ROAD_EDGE, (ROAD_RIGHT - 6, 0, 6, HEIGHT))

        # Broken white lane markings scroll downward to create motion.
        dash_height, gap = 42, 38
        offset = int(self.road_offset)
        for lane in range(1, LANE_COUNT):
            x = ROAD_LEFT + lane * LANE_WIDTH - 3
            y = -dash_height + offset
            while y < HEIGHT:
                pygame.draw.rect(self.screen, WHITE, (x, y, 6, dash_height), border_radius=3)
                y += dash_height + gap

        # Subtle roadside markers
        for y in range(-20 + offset % 60, HEIGHT, 60):
            pygame.draw.circle(self.screen, (80, 210, 115), (ROAD_LEFT - 18, y), 4)
            pygame.draw.circle(self.screen, (80, 210, 115), (ROAD_RIGHT + 18, y), 4)

    def draw_hud(self):
        # Header panel
        pygame.draw.rect(self.screen, (20, 24, 32), (0, 0, WIDTH, 76))
        pygame.draw.line(self.screen, (75, 85, 100), (0, 75), (WIDTH, 75), 2)
        draw_text(self.screen, f"SCORE  {self.score:06d}", self.font_medium, WHITE, (125, 28))
        draw_text(self.screen, f"BEST  {self.high_score:06d}", self.font_medium, YELLOW, (365, 28))
        config = self.DIFFICULTIES[self.difficulty]
        speed = config["base_speed"] + self.elapsed * config["speed_gain"]
        draw_text(self.screen, f"SPEED  {speed:04.1f}", self.font_medium, CYAN, (630, 28))
        draw_text(self.screen, f"MODE: {self.difficulty.upper()}  •  P: PAUSE",
                   self.font_small, (190, 200, 215), (WIDTH // 2, 57))

    def draw_menu(self):
        self.screen.fill(DARK)
        # Decorative neon road in the background
        pygame.draw.rect(self.screen, ROAD_GRAY, (250, 0, 300, HEIGHT))
        pygame.draw.line(self.screen, CYAN, (250, 0), (250, HEIGHT), 3)
        pygame.draw.line(self.screen, PURPLE, (550, 0), (550, HEIGHT), 3)
        for y in range(-30, HEIGHT, 90):
            pygame.draw.rect(self.screen, (180, 185, 195), (397, y, 6, 45), border_radius=3)

        draw_text(self.screen, "NEON HIGHWAY", self.font_title, CYAN, (WIDTH // 2, 115))
        draw_text(self.screen, "CAR RACING", self.font_medium, WHITE, (WIDTH // 2, 165))
        draw_text(self.screen, "Choose difficulty", self.font_small, (190, 200, 215), (WIDTH // 2, 250))

        for i, name in enumerate(self.difficulty_names):
            x = WIDTH // 2 + (i - self.difficulty_index) * 150
            selected = i == self.difficulty_index
            color = CYAN if selected else (115, 125, 140)
            rect = pygame.Rect(x - 62, 275, 124, 48)
            pygame.draw.rect(self.screen, (38, 45, 57), rect, border_radius=10)
            pygame.draw.rect(self.screen, color, rect, width=3 if selected else 1, border_radius=10)
            draw_text(self.screen, name, self.font_medium, color, rect.center)

        draw_text(self.screen, f"PERSONAL BEST  {self.high_score:06d}",
                   self.font_small, YELLOW, (WIDTH // 2, 365))
        draw_text(self.screen, "← / →  Select difficulty", self.font_small, WHITE, (WIDTH // 2, 425))
        draw_text(self.screen, "ENTER / SPACE  Start racing", self.font_medium, CYAN, (WIDTH // 2, 475))
        draw_text(self.screen, "Arrow keys to drive  •  P to pause  •  ESC for menu",
                   self.font_small, (180, 190, 205), (WIDTH // 2, 535))

    def draw_overlay(self, title, subtitle, accent=CYAN):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 8, 15, 190))
        self.screen.blit(overlay, (0, 0))
        pygame.draw.rect(self.screen, (28, 34, 45), (150, 175, 500, 250), border_radius=18)
        pygame.draw.rect(self.screen, accent, (150, 175, 500, 250), width=3, border_radius=18)
        draw_text(self.screen, title, self.font_large, accent, (WIDTH // 2, 230))
        draw_text(self.screen, subtitle, self.font_medium, WHITE, (WIDTH // 2, 285))

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
            return

        self.draw_road()
        for enemy in self.enemies:
            enemy.draw(self.screen)
        if self.player:
            self.player.draw(self.screen)
        self.draw_hud()

        if self.state == "paused":
            self.draw_overlay("PAUSED", "Press P or ENTER to resume", YELLOW)
        elif self.state == "game_over":
            self.draw_overlay("GAME OVER", f"Score: {self.score}   Best: {self.high_score}", RED)
            draw_text(self.screen, "ENTER / SPACE  Retry     M  Menu",
                      self.font_small, WHITE, (WIDTH // 2, 365))
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.handle_events()
            self.update(dt)
            self.draw()
            # draw() flips for game states; menu needs a flip too.
            if self.state == "menu":
                pygame.display.flip()

        self.stop_music()
        pygame.quit()


if __name__ == "__main__":
    Game().run()
