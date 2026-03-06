import pygame
import random
import sys
import os

pygame.init()

BASE_DIR = os.path.dirname(__file__)
ASSETS = os.path.join(BASE_DIR, "assets")

CARROT = "carrot"
APPLE = "apple"
SUGAR = "sugar"
MANURE = "manure"
STAR = "star_carrot"

WIDTH, HEIGHT = 900, 500
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Carrot Keeper")

clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 22)
big_font = pygame.font.SysFont(None, 26)

background_img = pygame.transform.scale(
    pygame.image.load(os.path.join(ASSETS, "background.png")).convert(),
    (WIDTH, HEIGHT)
)

player_img = pygame.transform.scale(
    pygame.image.load(os.path.join(ASSETS, "player.png")).convert_alpha(),
    (48,48)
)

carrot_img = pygame.transform.scale(
    pygame.image.load(os.path.join(ASSETS,"carrot_ready.png")).convert_alpha(),
    (28,28)
)

apple_img = pygame.transform.scale(
    pygame.image.load(os.path.join(ASSETS,"apple.png")).convert_alpha(),
    (28,28)
)

sugar_img = pygame.transform.scale(
    pygame.image.load(os.path.join(ASSETS,"sugar.png")).convert_alpha(),
    (28,28)
)

score = 0
level = 1
money = 0

def update_level():
    global level
    level = score // 30 + 1

def unlocked_products():

    products = [CARROT]

    if level >= 3:
        products.append(APPLE)

    if level >= 6:
        products.append(SUGAR)

    return products


def draw_panel(rect, alpha=170):
    panel = pygame.Surface((rect.width, rect.height))
    panel.set_alpha(alpha)
    panel.fill((255,255,255))
    screen.blit(panel, rect.topleft)

def darken_background(alpha=70):
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(alpha)
    overlay.fill((0,0,0))
    screen.blit(overlay,(0,0))


class Player:

    def __init__(self):

        self.rect = player_img.get_rect(center=(430,260))
        self.speed = 220
        self.capacity = 1

        self.inventory = {
            CARROT:0,
            APPLE:0,
            SUGAR:0,
            MANURE:0,
            STAR:0
        }

    def total_items(self):
        return sum(self.inventory.values())

    def update_capacity(self):
        self.capacity = 1 + level // 2

    def move(self,dt,keys):

        if keys[pygame.K_w]:
            self.rect.y -= self.speed * dt
        if keys[pygame.K_s]:
            self.rect.y += self.speed * dt
        if keys[pygame.K_a]:
            self.rect.x -= self.speed * dt
        if keys[pygame.K_d]:
            self.rect.x += self.speed * dt


class Field:

    def __init__(self):

        self.timer = 0
        self.grow_time = 4

        self.grid = []

        start_x = 60
        start_y = 120
        gap = 36

        rows = 5
        cols = 4

        for r in range(rows):
            for c in range(cols):

                rect = pygame.Rect(
                    start_x + c * gap,
                    start_y + r * gap,
                    28,
                    28
                )

                self.grid.append({
                    "rect": rect,
                    "product": None,
                    "star": False
                })

    def update(self,dt):

        self.timer += dt

        if self.timer >= self.grow_time:

            self.timer = 0

            empty_slots = [s for s in self.grid if s["product"] is None]

            if len(empty_slots) == 0:
                return

            slot = random.choice(empty_slots)

            product = random.choice(unlocked_products())

            slot["product"] = product
            slot["star"] = False


    def harvest(self,player):

        for slot in self.grid:

            if slot["product"] is None:
                continue

            if player.rect.colliderect(slot["rect"]):

                if player.total_items() < player.capacity:

                    if slot["star"]:
                        player.inventory[STAR] += 1
                        print("⭐ STAR CARROT HARVESTED!")

                    else:
                        player.inventory[slot["product"]] += 1

                    slot["product"] = None
                    slot["star"] = False
                    return


    def fertilize(self,player):

        if player.inventory[MANURE] <= 0:
            return

        for slot in self.grid:

            if slot["product"] == CARROT:

                dist = abs(player.rect.centerx - slot["rect"].centerx) + abs(player.rect.centery - slot["rect"].centery)

                if dist < 80:

                    slot["star"] = True
                    player.inventory[MANURE] -= 1
                    print("🌟 CARROT FERTILIZED!")
                    return


    def draw(self):

        for slot in self.grid:

            rect = slot["rect"]

            pygame.draw.rect(screen,(70,120,60),rect,1)

            if slot["product"] is None:
                continue

            if slot["product"] == CARROT:
                img = carrot_img
            elif slot["product"] == APPLE:
                img = apple_img
            else:
                img = sugar_img

            screen.blit(img,rect)

            if slot["star"]:
                pygame.draw.rect(screen,(255,215,0),rect,3)
                pygame.draw.circle(screen,(255,240,120),rect.center,6)


class Horse:

    def __init__(self,x,y):

        self.rect = pygame.Rect(x,y,96,64)

        self.max_health = 100
        self.health = 100

        self.request_active = False
        self.request_timer = 0
        self.request_duration = 0

        self.food_request = {}
        self.food_given = {}

        self.feed_cooldown = 0

        self.rest_timer = 0
        self.rest_duration = random.uniform(4,7)

    def start_request(self):

        self.request_active = True
        self.request_timer = 0
        self.food_given = {}

        product = random.choice(unlocked_products())

        if level < 4:
            amount = 1
        elif level < 8:
            amount = random.choice([1,2])
        else:
            amount = random.choice([2,3])

        self.food_request = {product:amount}

        base_time = 7 - min(level * 0.4, 3)

        self.request_duration = random.uniform(base_time, base_time + 2)


    def end_request(self):

        success = True

        for p in self.food_request:

            if self.food_given.get(p,0) < self.food_request[p]:
                success = False

        global score, money

        if success:

            score += 10
            money += 5

            mx = self.rect.centerx + random.randint(-20,20)
            my = self.rect.bottom + random.randint(0,10)

            manures.append(pygame.Rect(mx,my,20,20))

        else:
            self.health = max(0,self.health-5)

        self.request_active = False
        self.food_request = {}
        self.food_given = {}

        self.rest_timer = 0
        self.rest_duration = random.uniform(6 + level*0.5, 8 + level*0.7)


    def update(self,dt):

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


    def feed(self,player):

        if player.inventory[STAR] > 0:

            player.inventory[STAR] -= 1

            global score
            score += 25

            self.request_active = False

            self.rest_duration = random.uniform(14 + level, 18 + level)

            return True


        if not self.request_active:
            return False

        if self.feed_cooldown > 0:
            return False


        for product in self.food_request:

            needed = self.food_request[product]
            given = self.food_given.get(product,0)

            if given >= needed:
                return False

            if player.inventory[product] > 0:

                player.inventory[product] -= 1
                self.food_given[product] = given + 1
                self.feed_cooldown = 0.6

                if self.food_given[product] >= self.food_request[product]:
                    self.end_request()

                return True

        return False


    def draw(self):

        panel_rect = pygame.Rect(self.rect.x-6,self.rect.y-46,120,44)
        draw_panel(panel_rect,180)

        hp_ratio = self.health/self.max_health

        pygame.draw.rect(screen,(220,220,220),(panel_rect.x+6,panel_rect.y+6,108,6))
        pygame.draw.rect(screen,(80,180,80),(panel_rect.x+6,panel_rect.y+6,108*hp_ratio,6))

        if self.request_active:

            text=""

            for p in self.food_request:

                given = self.food_given.get(p,0)
                needed = self.food_request[p]

                text += f"{p[0].upper()}:{given}/{needed} "

            txt = font.render(text,True,(40,40,40))
            screen.blit(txt,(panel_rect.x+6,panel_rect.y+16))


player = Player()
field = Field()

horses = [
    Horse(640,85),
    Horse(640,215),
    Horse(640,345)
]

manures = []
sell_box = pygame.Rect(500,420,80,60)


while True:

    dt = clock.tick(60)/1000

    update_level()
    player.update_capacity()

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_m:
                field.fertilize(player)

    keys = pygame.key.get_pressed()
    player.move(dt,keys)

    field.update(dt)
    field.harvest(player)

    screen.blit(background_img,(0,0))
    darken_background(70)

    field.draw()

    for m in manures:

        if player.rect.colliderect(m):

            if player.total_items() < player.capacity:

                player.inventory[MANURE] += 1
                manures.remove(m)
                break

    for m in manures:
        pygame.draw.circle(screen,(120,80,40),m.center,8)

    if player.rect.colliderect(sell_box):

        if player.inventory[MANURE] > 0:

            player.inventory[MANURE] -= 1
            money += 3

    pygame.draw.rect(screen,(150,100,50),sell_box)
    txt = font.render("SELL",True,(255,255,255))
    screen.blit(txt,(sell_box.x+15,sell_box.y+20))

    for h in horses:

        h.update(dt)

        if player.rect.colliderect(h.rect):
            h.feed(player)

        h.draw()

    screen.blit(player_img,player.rect)

    top_panel = pygame.Rect(10,8,520,32)
    draw_panel(top_panel,180)

    inv_text = f"🥕{player.inventory[CARROT]} 🍎{player.inventory[APPLE]} 🍬{player.inventory[SUGAR]} 💩{player.inventory[MANURE]} ⭐{player.inventory[STAR]}"

    ui = big_font.render(
        f"Score:{score} Level:{level} Money:{money} {inv_text} Cap:{player.capacity}",
        True,(40,40,40)
    )

    screen.blit(ui,(20,14))

    pygame.display.flip()