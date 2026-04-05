import pygame
import random
import math
from typing import List, Optional
import constants
from enums import FoodType, HorseState, PlayerState, CropState

class Poop:
    """Extra income collectible"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = constants.POOP_SIZE
        
    def draw(self, screen, sprites):
        spr = sprites.get('poop')
        if spr:
            screen.blit(spr, (int(self.x - self.size[0]//2), int(self.y - self.size[1]//2)))
        else:
            pygame.draw.circle(screen, (100, 70, 20), (int(self.x), int(self.y)), 15)

class Crop:
    """Level 1 Carrot crop"""
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.state = CropState.SEED
        self.timer = 0.0
        self.growth_time = constants.GROWTH_TIME_CARROT
        
    def update(self, dt):
        if self.state == CropState.SEED:
            self.timer += dt
            if self.timer >= self.growth_time:
                self.state = CropState.MATURE
    
    def draw(self, screen, sprites):
        growth = self.timer / self.growth_time
        if self.state == CropState.MATURE:
            spr = sprites.get('crop_mature')
            if spr:
                # Mature size: 30x36
                scaled = pygame.transform.smoothscale(spr, (30, 36))
                screen.blit(scaled, (int(self.x - 15), int(self.y - 18)))
        else:
            spr = sprites.get('crop_seed')
            if spr:
                # Progressive growth size (from 10 to 22px)
                size = int(10 + 12 * growth)
                scaled = pygame.transform.smoothscale(spr, (size, size))
                screen.blit(scaled, (int(self.x - size//2), int(self.y - size//2)))

class AppleTree:
    """Level 2 Apple Tree"""
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.state = "SEED" # SEED, STAGE1, STAGE2, READY
        self.timer = 0.0
        self.apples_left = 3
        self.growth_time = constants.GROWTH_TIME_APPLE_TREE
        
    def update(self, dt):
        if self.state != "READY":
            self.timer += dt
            if self.timer >= self.growth_time:
                self.state = "READY"
            elif self.timer >= self.growth_time * 0.8:
                self.state = "STAGE4"
            elif self.timer >= self.growth_time * 0.6:
                self.state = "STAGE3"
            elif self.timer >= self.growth_time * 0.4:
                self.state = "STAGE2"
            elif self.timer >= self.growth_time * 0.2:
                self.state = "STAGE1"
                
    def harvest(self) -> bool:
        if self.state == "READY" and self.apples_left > 0:
            self.apples_left -= 1
            return True
        return False
        
    def draw(self, screen, sprites):
        growth_ratio = min(1.0, self.timer / self.growth_time)
        # Smoothly scale from 30px to 120px
        current_size = int(30 + (120 - 30) * growth_ratio)
        
        # Use agac_4 for growth, agac_5 for final READY state
        spr_name = 'agac_4' if growth_ratio < 1.0 else 'agac_5'
        
        spr = sprites.get(spr_name)
        if spr:
            scaled = pygame.transform.smoothscale(spr, (current_size, current_size))
            screen.blit(scaled, (int(self.x - current_size//2), int(self.y - current_size//2)))
            
        if self.state == "READY" and self.apples_left > 0:
            apple_spr = sprites.get('apple')
            if apple_spr:
                # Draw remaining apples
                offsets = [(-15, -10), (15, -15), (0, 10)]
                for i in range(self.apples_left):
                    ox, oy = offsets[i]
                    screen.blit(apple_spr, (int(self.x + ox - 10), int(self.y + oy - 10)))
            

class Horse:
    def __init__(self, spawn_index: int, level: int = 1, can_have_three: bool = True):
        self.x = constants.HORSES_START + 50
        self.y = 100 + spawn_index * 180
        self.spawn_index = spawn_index
        self.state = HorseState.WAITING
        self.max_time = 80.0 if level == 1 else 60.0
        self.remaining_time = self.max_time
        self.previous_count = 0
        self.feedings_count = 0
        
        # New requirements logic
        self.wanted_items = self._generate_requests(level, can_have_three)
        self.initial_count = len(self.wanted_items)
        self.fed_items: List[FoodType] = [] # Track what has been fed

    def _generate_requests(self, level: int, can_have_three: bool = True) -> List[FoodType]:
        max_items = 3 if can_have_three else 2
        choices = [n for n in range(1, max_items + 1) if n != self.previous_count]
        if not choices: choices = [1] # Fallback
        num_items = random.choice(choices)
        self.previous_count = num_items
        if level == 1:
            return [FoodType.CARROT] * num_items
        else:
            # Level 2+: Random mix of carrots and apples
            # To ensure it's not ONLY apples, we just pick randomly for each slot.
            return [random.choice([FoodType.CARROT, FoodType.APPLE]) for _ in range(num_items)]

    def update(self, dt) -> Optional[Poop]:
        if self.state == HorseState.WAITING:
            self.remaining_time -= dt
            if self.remaining_time <= 0:
                self.state = HorseState.SICK
        return None

    def receive_food(self, food_type: FoodType) -> bool:
        if self.state == HorseState.WAITING and self.wanted_items:
            if food_type in self.wanted_items:
                self.wanted_items.remove(food_type)
                self.fed_items.append(food_type) # Track the fed item
                return True
        return False

    def is_finished(self) -> bool:
        return len(self.wanted_items) == 0

    def reset(self, level: int, can_have_three: bool = True):
        # Keep x and y, just reset state and items
        self.state = HorseState.WAITING
        self.remaining_time = 80.0 if level == 1 else 60.0
        self.max_time = self.remaining_time
        self.fed_items = []
        self.wanted_items = self._generate_requests(level, can_have_three)
        self.initial_count = len(self.wanted_items)
        self.feedings_count += 1

    def draw(self, screen, sprites):
        spr = sprites.get('horse')
        if spr:
            # Center of right column is roughly 880 (750 + (1024-750)/2)
            screen.blit(spr, (int(self.x - 90), int(self.y - 55)))
            
        # UI overlays (Health Bar and Bubble)
        if self.state == HorseState.WAITING:
            # Health bar above horse
            bar_w = 100
            fill_w = int(bar_w * (self.remaining_time / self.max_time))
            pygame.draw.rect(screen, (50, 50, 50), (self.x - 50, self.y - 75, bar_w, 8))
            pygame.draw.rect(screen, (0, 255, 0), (self.x - 50, self.y - 75, fill_w, 8))
            
            # Logic: `fed_items` are FULL color, `wanted_items` are LOW opacity.
            # We show `fed_items` first, then `wanted_items`.
            all_icons = self.fed_items + self.wanted_items
            
            for i, item_type in enumerate(all_icons):
                bx = self.x - 140 - i * 45
                by = self.y - 15
                
                spr_name = 'carrot' if item_type == FoodType.CARROT else 'apple'
                s = sprites.get(spr_name)
                
                if s:
                    # Draw circular bubble background
                    pygame.draw.circle(screen, (255, 255, 255, 180), (int(bx + 18), int(by + 18)), 22)
                    
                    # Create a copy to adjust alpha
                    icon_spr = pygame.transform.scale(s, (35, 35)).copy()
                    if i >= len(self.fed_items):
                        # Still needed -> Low opacity
                        icon_spr.set_alpha(80) # 80/255 opacity
                    else:
                        # Already fed -> Full opacity
                        icon_spr.set_alpha(255)
                        
                    screen.blit(icon_spr, (int(bx), int(by)))

class Player:
    def __init__(self):
        self.x = constants.SCREEN_WIDTH // 2
        self.y = constants.SCREEN_HEIGHT // 2
        self.speed = 240
        self.state = PlayerState.EMPTY
        self.carrying_item: Optional[str] = None # "CARROT", "APPLE", "POOP", "SEED", "SAPLING"
        
        self.coins = constants.INITIAL_COINS
        self.carrot_seeds = 0
        self.apple_saplings = 0
        
    def move(self, keys, dt):
        dx, dy = 0, 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy += 1
        
        length = math.sqrt(dx*dx + dy*dy)
        if length > 0:
            self.x += (dx/length) * self.speed * dt
            self.y += (dy/length) * self.speed * dt
            
        # Bound to screen
        self.x = max(20, min(constants.SCREEN_WIDTH - 20, self.x))
        self.y = max(20, min(constants.SCREEN_HEIGHT - 20, self.y))

    def draw(self, screen, sprites):
        spr = sprites.get('player')
        if spr:
            screen.blit(spr, (int(self.x - 18), int(self.y - 22)))
            
        if self.state != PlayerState.EMPTY and self.carrying_item:
            item_spr_name = self.carrying_item.lower()
            if self.carrying_item == "SEED": item_spr_name = 'crop_seed'
            elif self.carrying_item == "SAPLING": item_spr_name = 'agac_1'
            
            item_spr = sprites.get(item_spr_name)
            if item_spr:
                sw, sh = item_spr.get_size()
                scale = 30 / max(sw, sh)
                scaled = pygame.transform.smoothscale(item_spr, (int(sw*scale), int(sh*scale)))
                screen.blit(scaled, (int(self.x - scaled.get_width()//2), int(self.y - 50)))
