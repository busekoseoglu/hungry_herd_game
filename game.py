import pygame
import random
import sys
import os

pygame.init()

# --------------------
# PATHS
# --------------------
BASE_DIR = os.path.dirname(__file__)
ASSETS = os.path.join(BASE_DIR, "assets")

# --------------------
# WINDOW
# --------------------
WIDTH, HEIGHT = 900, 500
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Carrot Keeper")

clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 22)
big_font = pygame.font.SysFont(None, 26)

# --------------------
# SPRITE SIZES
# --------------------
PLAYER_SIZE = (48, 48)
HORSE_SIZE = (96, 64)

# --------------------
# LOAD & SCALE SPRITES
# --------------------
background_img = pygame.transform.scale(
    pygame.image.load(os.path.join(ASSETS, "background.png")).convert(),
    (WIDTH, HEIGHT)
)

player_img = pygame.transform.scale(
    pygame.image.load(os.path.join(ASSETS, "player.png")).convert_alpha(),
    PLAYER_SIZE
)

horse_img = pygame.transform.scale(
    pygame.image.load(os.path.join(ASSETS, "horse.png")).convert_alpha(),
    HORSE_SIZE
)

# --------------------
# GAME STATE
# --------------------
score = 0
level = 1

def update_level():
    global level
    level = score // 100 + 1

# --------------------
# UI HELPERS
# --------------------
def draw_panel(rect, alpha=170):
    panel = pygame.Surface((rect.width, rect.height))
    panel.set_alpha(alpha)
    panel.fill((255, 255, 255))
    screen.blit(panel, rect.topleft)

def darken_background(alpha=70):
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(alpha)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

# --------------------
# PLAYER
# --------------------
class Player:
    def __init__(self):
        self.rect = player_img.get_rect(center=(430, 260))
        self.speed = 220
        self.capacity = 1
        self.carry = 0

    def move(self, dt, keys):
        if keys[pygame.K_w]:
            self.rect.y -= self.speed * dt
        if keys[pygame.K_s]:
            self.rect.y += self.speed * dt
        if keys[pygame.K_a]:
            self.rect.x -= self.speed * dt
        if keys[pygame.K_d]:
            self.rect.x += self.speed * dt

# --------------------
# CARROT FIELD (LOGIC ONLY)
# --------------------
class CarrotField:
    def __init__(self):
        self.timer = 0
        self.grow_time = 4
        self.available = 0

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.grow_time:
            self.available += 1
            self.timer = 0

    def harvest(self):
        if self.available > 0:
            self.available -= 1
            return True
        return False

# --------------------
# HORSE
# --------------------
class Horse:
    def __init__(self, x, y):
        # GÖRÜNMEZ RECT – arka plandaki ata karşılık gelir
        self.rect = pygame.Rect(x, y, 96, 64)

        self.max_health = 100
        self.health = 100

        self.request_active = False
        self.request_timer = 0
        self.request_duration = 0

        self.food_needed = 0
        self.food_given = 0

        self.feed_cooldown = 0

        self.rest_timer = 0
        self.rest_duration = random.uniform(4, 7)

    def start_request(self):
        self.request_active = True
        self.request_timer = 0
        self.food_given = 0
        self.feed_cooldown = 0

        self.food_needed = random.choice([1, 2])
        self.request_duration = random.uniform(5, 7)

    def end_request(self):
        if self.food_given < self.food_needed:
            self.health = max(0, self.health - 5)

        self.request_active = False
        self.food_given = 0
        self.request_timer = 0
        self.rest_timer = 0
        self.rest_duration = random.uniform(4, 7)

    def update(self, dt):
        if self.feed_cooldown > 0:
            self.feed_cooldown -= dt

        if not self.request_active:
            self.rest_timer += dt
            if self.rest_timer >= self.rest_duration:
                self.start_request()
        else:
            self.request_timer += dt
            if self.request_timer >= self.request_duration:
                self.end_request()

    def feed(self):
        if not self.request_active:
            return False
        if self.feed_cooldown > 0:
            return False

        self.food_given += 1
        self.feed_cooldown = 0.6
        return True

    def draw(self):
        # ❗ AT ÇİZİLMİYOR – SADECE UI VAR
        panel_rect = pygame.Rect(self.rect.x - 6, self.rect.y - 46, 110, 44)
        draw_panel(panel_rect, 180)

        hp_ratio = self.health / self.max_health
        pygame.draw.rect(screen, (220, 220, 220),
                         (panel_rect.x + 6, panel_rect.y + 6, 98, 6))
        pygame.draw.rect(screen, (80, 180, 80),
                         (panel_rect.x + 6, panel_rect.y + 6, 98 * hp_ratio, 6))

        if self.request_active:
            txt = font.render(
                f"{self.food_given}/{self.food_needed} 🥕",
                True, (40, 40, 40)
            )
            screen.blit(txt, (panel_rect.x + 6, panel_rect.y + 16))

            time_left = max(0, self.request_duration - self.request_timer)
            bar_w = 98 * (time_left / self.request_duration)
            pygame.draw.rect(
                screen, (240, 200, 80),
                (panel_rect.x + 6, panel_rect.y + 30, bar_w, 4)
            )

# --------------------
# SETUP
# --------------------
player = Player()
carrot_field = CarrotField()

horses = [
    Horse(640, 85),
    Horse(640, 215),
    Horse(640, 345),
]

# --------------------
# MAIN LOOP
# --------------------
while True:
    dt = clock.tick(60) / 1000
    update_level()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    keys = pygame.key.get_pressed()
    player.move(dt, keys)

    carrot_field.update(dt)

    screen.blit(background_img, (0, 0))
    darken_background(70)

    for h in horses:
        h.update(dt)

        if player.rect.colliderect(h.rect) and player.carry > 0:
            if h.feed():
                player.carry -= 1
                score += 5

        h.draw()

    if player.rect.x < 300:
        if carrot_field.harvest() and player.carry < player.capacity:
            player.carry += 1

    screen.blit(player_img, player.rect)

    top_panel = pygame.Rect(10, 8, 340, 32)
    draw_panel(top_panel, 180)

    ui = big_font.render(
        f"Score: {score}   Level: {level}   Carry: {player.carry}/{player.capacity}",
        True, (40, 40, 40)
    )
    screen.blit(ui, (20, 14))

    pygame.display.flip()
