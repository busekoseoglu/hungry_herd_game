"""
Farmer's Harvest - New Game Architecture
Core Loop: Harvest → Feed → Produce → Sell → Upgrade
"""

import pygame
import sys
import random
import os
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional
import math

# ============ INITIALIZATION ============
pygame.init()

# ============ GAME SETTINGS ============
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 700
FPS = 60

# ============ COLORS ============
COLOR_GRASS = (180, 220, 100)
COLOR_BROWN = (139, 69, 19)
COLOR_DARK_BROWN = (101, 50, 15)
COLOR_ORANGE = (255, 165, 0)
COLOR_RED = (220, 20, 60)
COLOR_YELLOW = (255, 255, 0)
COLOR_GREEN = (0, 200, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_BLUE = (0, 100, 255)
COLOR_GRAY = (128, 128, 128)

# ============ GAME ZONES ============
FARM_AREA = pygame.Rect(0, 0, 400, SCREEN_HEIGHT)
HORSE_AREA = pygame.Rect(SCREEN_WIDTH - 200, 0, 200, SCREEN_HEIGHT)
SELL_ZONE = pygame.Rect(SCREEN_WIDTH//2 - 50, SCREEN_HEIGHT - 80, 100, 60)

# ============ ENUMS ============
class GameState(Enum):
    MENU = "menu"
    PLAYING = "playing" 
    SHOP = "shop"
    GAME_OVER = "game_over"

class CropType(Enum):
    CARROT = "carrot"
    APPLE = "apple"
    WHEAT = "wheat"

class HorseState(Enum):
    WAITING = "waiting"
    REQUESTING = "requesting"
    FED = "fed"
    PRODUCING = "producing"
    UNHAPPY = "unhappy"

# ============ DATA CLASSES ============
@dataclass
class Upgrade:
    name: str
    cost: int
    description: str
    effect: callable
    purchased: bool = False

@dataclass
class Crop:
    x: float
    y: float
    type: CropType
    growth_stage: int  # 0: seed, 1: growing, 2: mature
    growth_timer: float
    
@dataclass
class Horse:
    x: float
    y: float
    health: int
    max_health: int
    state: HorseState
    requests: List[CropType] = None  # Multiple food requests
    request_timer: float = 0.0
    produce_timer: float = 0.0
    fed_amount: int = 0  # Track how much of the request is fulfilled

# ============ CORE CLASSES ============
class Farmer:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.speed = 240  # 20% faster than original 200
        self.carry_capacity = 1
        self.inventory: Dict[CropType, int] = {CropType.CARROT: 0, CropType.APPLE: 0, CropType.WHEAT: 0}
        self.money = 0
        self.rect = pygame.Rect(x, y, 96, 96)  # Updated to match larger player size
    
    def move(self, dt: float, keys):
        dx = dy = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy = -self.speed * dt
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy = self.speed * dt
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx = -self.speed * dt
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx = self.speed * dt
        
        self.x += dx
        self.y += dy
        self.rect.x = self.x
        self.rect.y = self.y
        
        # Keep player on screen
        self.x = max(0, min(self.x, SCREEN_WIDTH - self.rect.width))
        self.y = max(0, min(self.y, SCREEN_HEIGHT - self.rect.height))
        self.rect.x = self.x
        self.rect.y = self.y
    
    def total_items(self) -> int:
        return sum(self.inventory.values())
    
    def can_carry(self) -> bool:
        return self.total_items() < self.carry_capacity
    
    def add_crop(self, crop_type: CropType) -> bool:
        if self.can_carry():
            self.inventory[crop_type] += 1
            return True
        return False
    
    def remove_crop(self, crop_type: CropType) -> bool:
        if self.inventory[crop_type] > 0:
            self.inventory[crop_type] -= 1
            return True
        return False

class Field:
    def __init__(self):
        self.crops: List[Crop] = []
        self.spawn_timer = 0.0
        self.spawn_interval = 3.0  # seconds between spawns
        self.growth_time = 4.0  # seconds to grow from seed to mature
        
        # Create initial crop grid
        self._create_crop_grid()
    
    def _create_crop_grid(self):
        start_x = 50
        start_y = 100
        spacing_x = 80
        spacing_y = 80
        
        # Start with 2 carrot and 2 apple plots
        initial_plots = [
            CropType.CARROT, CropType.CARROT,
            CropType.APPLE, CropType.APPLE
        ]
        
        for i, crop_type in enumerate(initial_plots):
            x = start_x + (i % 2) * spacing_x
            y = start_y + (i // 2) * spacing_y
            self.crops.append(Crop(x, y, crop_type, 0, 0))
    
    def update(self, dt: float):
        # Update spawn timer
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            self._spawn_new_crop()
        
        # Update crop growth
        for crop in self.crops:
            if crop.growth_stage < 2:
                crop.growth_timer += dt
                if crop.growth_timer >= self.growth_time:
                    crop.growth_stage += 1
                    crop.growth_timer = 0
    
    def _spawn_new_crop(self):
        # Find empty spots (crops that have been harvested)
        empty_spots = [c for c in self.crops if c.growth_stage == 0 and c.growth_timer == 0]
        if empty_spots:
            crop = random.choice(empty_spots)
            crop.growth_timer = 0.1  # Mark as planted
            # Keep the original crop type - don't randomly change it!
    
    def add_plot(self, crop_type: CropType):
        # Find a good spot for new plot
        start_x = 50
        start_y = 100
        spacing_x = 80
        spacing_y = 80
        
        # Find empty spot (build beneath current crops)
        for col in range(4):
            for row in range(6):
                x = start_x + col * spacing_x
                y = start_y + row * spacing_y
                
                # Check if spot is empty
                occupied = False
                for crop in self.crops:
                    if abs(crop.x - x) < 20 and abs(crop.y - y) < 20:
                        occupied = True
                        break
                
                if not occupied:
                    self.crops.append(Crop(x, y, crop_type, 0, 0))
                    return
    
    def harvest_crop(self, farmer: Farmer) -> bool:
        for crop in self.crops:
            if crop.growth_stage == 2:  # Mature
                crop_rect = pygame.Rect(crop.x - 20, crop.y - 20, 40, 40)
                if farmer.rect.colliderect(crop_rect):
                    if farmer.add_crop(crop.type):
                        # Reset crop to seed
                        crop.growth_stage = 0
                        crop.growth_timer = 0
                        return True
        return False

class HorseManager:
    def __init__(self):
        self.horses: List[Horse] = []
        self._create_horses()
    
    def _create_horses(self):
        positions = [
            (SCREEN_WIDTH - 150, 150),
            (SCREEN_WIDTH - 150, 350)
            # Third horse will be added later via upgrade
        ]
        
        for x, y in positions:
            horse = Horse(x, y, 100, 100, HorseState.WAITING)
            horse.requests = []  # Initialize empty requests list
            self.horses.append(horse)
    
    def update(self, dt: float, game_level: int):
        for horse in self.horses:
            self._update_horse(horse, dt, game_level)
    
    def _update_horse(self, horse: Horse, dt: float, game_level: int):
        if horse.state == HorseState.WAITING:
            # Random chance to start requesting
            if random.random() < 0.01:  # 1% chance per frame
                horse.state = HorseState.REQUESTING
                horse.fed_amount = 0  # Reset fed amount
                
                # Level-based food requirements
                if game_level == 1:
                    # Level 1: 1 food
                    available_crops = [CropType.CARROT, CropType.APPLE]
                    horse.requests = [random.choice(available_crops)]
                elif game_level == 2:
                    # Level 2: 2 foods
                    available_crops = [CropType.CARROT, CropType.APPLE, CropType.WHEAT]
                    horse.requests = [random.choice(available_crops), random.choice(available_crops)]
                elif game_level == 3:
                    # Level 3: 2 foods (same as level 2)
                    available_crops = [CropType.CARROT, CropType.APPLE, CropType.WHEAT]
                    horse.requests = [random.choice(available_crops), random.choice(available_crops)]
                else:  # Level 4+
                    # Level 4+: 3 foods
                    available_crops = [CropType.CARROT, CropType.APPLE, CropType.WHEAT]
                    horse.requests = [random.choice(available_crops), random.choice(available_crops), random.choice(available_crops)]
                
                horse.request_timer = 30.0  # 30 seconds to fulfill
        
        elif horse.state == HorseState.REQUESTING:
            horse.request_timer -= dt
            if horse.request_timer <= 0:
                # Failed to fulfill request
                horse.health -= 20
                horse.state = HorseState.UNHAPPY
                horse.requests = []  # Clear requests
                horse.fed_amount = 0
                horse.request_timer = 5.0  # Wait before next request
        
        elif horse.state == HorseState.FED:
            horse.produce_timer -= dt
            if horse.produce_timer <= 0:
                horse.state = HorseState.PRODUCING
        
        elif horse.state == HorseState.PRODUCING:
            # Produce manure (handled in game loop)
            horse.state = HorseState.WAITING
        
        elif horse.state == HorseState.UNHAPPY:
            horse.request_timer -= dt
            if horse.request_timer <= 0:
                horse.state = HorseState.WAITING
    
    def feed_horse(self, farmer: Farmer) -> bool:
        for horse in self.horses:
            if horse.state == HorseState.REQUESTING:
                horse_rect = pygame.Rect(horse.x - 40, horse.y - 30, 80, 60)
                if farmer.rect.colliderect(horse_rect):
                    if farmer.remove_crop(horse.request):
                        horse.state = HorseState.FED
                        horse.produce_timer = 3.0  # 3 seconds to produce
                        horse.request = None
                        
                        # 33% chance to produce manure
                        if random.random() < 0.33:
                            return True  # Signal that manure was produced
                        return False  # Fed but no manure
        return False

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Farmer's Harvest")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        self.state = GameState.PLAYING
        self.running = True
        
        # Game objects
        self.farmer = Farmer(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.field = Field()
        self.horse_manager = HorseManager()
        
        # Manure system
        self.manure_patches: List[pygame.Rect] = []
        
        # Level system
        self.total_feedings = 0
        self.current_level = 1
        
        # Shop system
        self._init_upgrades()
        
        # Load assets
        self._load_assets()
    
    def _init_upgrades(self):
        self.upgrades = {
            'carry': {
                'level': 0,
                'cost': 5,
                'name': 'Extra Carry Size',
                'description': 'Carry 1 more crop',
                'max_level': 5
            },
            'speed': {
                'level': 0,
                'cost': 10,
                'name': '10% Faster',
                'description': 'Move 10% faster',
                'max_level': 5
            },
            'carrot_plot': {
                'level': 0,
                'cost': 8,
                'name': 'Plant Carrot',
                'description': 'Add 1 carrot plot',
                'max_level': 10
            },
            'apple_plot': {
                'level': 0,
                'cost': 8,
                'name': 'Plant Apple', 
                'description': 'Add 1 apple plot',
                'max_level': 10
            },
            'wheat_plot': {
                'level': 0,
                'cost': 5,  # Changed from 12 to 5
                'name': 'Plant Wheat',
                'description': 'Add 1 wheat plot',
                'max_level': 10
            }
        }
    
    def _load_assets(self):
        # Load PNG graphics
        try:
            self.player_img = pygame.image.load("assets/player.png").convert_alpha()
            self.horse_img = pygame.image.load("assets/horse.png").convert_alpha()
            self.carrot_img = pygame.image.load("assets/carrot.png").convert_alpha()
            self.apple_img = pygame.image.load("assets/redapple.png").convert_alpha()
            self.wheat_img = pygame.image.load("assets/wheat.png").convert_alpha()
            self.manure_img = pygame.image.load("assets/manure.png").convert_alpha()
            
            # Scale images if needed
            self.player_img = pygame.transform.scale(self.player_img, (96, 96))  # 2x larger
            self.horse_img = pygame.transform.scale(self.horse_img, (80, 60))
            self.carrot_img = pygame.transform.scale(self.carrot_img, (60, 60))  # 3x larger
            self.apple_img = pygame.transform.scale(self.apple_img, (60, 60))    # 3x larger
            self.wheat_img = pygame.transform.scale(self.wheat_img, (60, 60))     # 3x larger
            self.manure_img = pygame.transform.scale(self.manure_img, (30, 30))  # 30x30 pixels
            
            # Create mini versions for player inventory display
            self.mini_carrot_img = pygame.transform.scale(self.carrot_img, (15, 15))
            self.mini_apple_img = pygame.transform.scale(self.apple_img, (15, 15))
            self.mini_wheat_img = pygame.transform.scale(self.wheat_img, (15, 15))
            self.mini_manure_img = pygame.transform.scale(self.manure_img, (15, 15))
            
            print("✅ All graphics loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading graphics: {e}")
            print("🔄 Using colored rectangles as fallback")
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == GameState.PLAYING:
                        self.state = GameState.MENU
                    elif self.state == GameState.MENU:
                        self.running = False
                elif event.key == pygame.K_SPACE:
                    if self.state == GameState.PLAYING:
                        # Harvest crops
                        self.field.harvest_crop(self.farmer)
                        # Feed horses and track feeding regardless of manure
                        horse_fed = False
                        for horse in self.horse_manager.horses:
                            if horse.state == HorseState.REQUESTING:
                                horse_rect = pygame.Rect(horse.x - 40, horse.y - 30, 80, 60)
                                if self.farmer.rect.colliderect(horse_rect):
                                    # Check if we can fulfill any of the horse's requests
                                    for i, requested_crop in enumerate(horse.requests):
                                        if self.farmer.remove_crop(requested_crop):
                                            horse.fed_amount += 1
                                            self.total_feedings += 1  # Count EVERY feeding
                                            horse_fed = True
                                            
                                            # Remove the fulfilled request
                                            horse.requests.pop(i)
                                            break
                                    
                                    # Check if all requests are fulfilled
                                    if len(horse.requests) == 0:
                                        horse.state = HorseState.FED
                                        horse.produce_timer = 3.0  # 3 seconds to produce
                                        horse.fed_amount = 0
                                        
                                        # 90% chance to produce manure
                                        if random.random() < 0.9:
                                            manure_x = horse.x - 15  # Center under horse (30x30 size)
                                            manure_y = horse.y + 35  # Right under horse
                                            self.manure_patches.append(pygame.Rect(manure_x, manure_y, 30, 30))
                                    break
                elif event.key == pygame.K_p:
                    # Toggle shop
                    if self.state == GameState.PLAYING:
                        self.state = GameState.SHOP
                    elif self.state == GameState.SHOP:
                        self.state = GameState.PLAYING
                # Shop purchases
                elif self.state == GameState.SHOP:
                    for key, upgrade_key in [(pygame.K_1, 'carry'), (pygame.K_2, 'speed'), 
                                           (pygame.K_3, 'carrot_plot'), (pygame.K_4, 'apple_plot'), 
                                           (pygame.K_5, 'wheat_plot')]:
                        if event.key == key:
                            upgrade = self.upgrades[upgrade_key]
                            if upgrade['level'] < upgrade['max_level']:
                                if self.farmer.money >= upgrade['cost']:
                                    self.farmer.money -= upgrade['cost']
                                    upgrade['level'] += 1
                                    upgrade['cost'] = int(upgrade['cost'] * 1.5)  # Increase cost for next level
                                    
                                    # Apply upgrade effects
                                    if upgrade_key == 'carry':
                                        self.farmer.carry_capacity += 1
                                    elif upgrade_key == 'speed':
                                        self.farmer.speed = int(self.farmer.speed * 1.1)
                                    elif upgrade_key in ['carrot_plot', 'apple_plot', 'wheat_plot']:
                                        crop_type = CropType.CARROT if upgrade_key == 'carrot_plot' else \
                                                  CropType.APPLE if upgrade_key == 'apple_plot' else CropType.WHEAT
                                        self.field.add_plot(crop_type)
    
    def update(self, dt: float):
        if self.state == GameState.PLAYING:
            keys = pygame.key.get_pressed()
            self.farmer.move(dt, keys)
            self.field.update(dt)
            self.horse_manager.update(dt, self.current_level)
            
            # Check for manure collection
            self._collect_manure()
            
            # Check for selling
            self._sell_manure()
            
            # Check level progression
            self._check_level_progression()
    
    def _check_level_progression(self):
        # Level 2: After 6 total feedings
        if self.current_level == 1 and self.total_feedings >= 6:
            self.current_level = 2
            # Show level up message
            print(f"LEVEL UP! Now horses can demand wheat!")
        
        # Level 3: After 10 total feedings
        elif self.current_level == 2 and self.total_feedings >= 10:
            self.current_level = 3
            # Add third horse
            new_horse = Horse(SCREEN_WIDTH - 150, 550, 100, 100, HorseState.WAITING)
            new_horse.requests = []  # Initialize empty requests list
            self.horse_manager.horses.append(new_horse)
            print(f"LEVEL UP! Third horse added!")
    
    def _collect_manure(self):
        for manure in self.manure_patches[:]:
            if self.farmer.rect.colliderect(manure):
                self.manure_patches.remove(manure)
                # Add manure to farmer's inventory
                if 'manure' not in self.farmer.inventory:
                    self.farmer.inventory['manure'] = 0
                self.farmer.inventory['manure'] += 1
    
    def _sell_manure(self):
        if self.farmer.rect.colliderect(SELL_ZONE):
            # Sell all manure for $5 each
            if 'manure' in self.farmer.inventory and self.farmer.inventory['manure'] > 0:
                manure_sold = self.farmer.inventory['manure']
                self.farmer.money += manure_sold * 5
                self.farmer.inventory['manure'] = 0
    
    def draw(self):
        self.screen.fill(COLOR_GRASS)
        
        if self.state == GameState.PLAYING:
            self._draw_game()
        elif self.state == GameState.SHOP:
            self._draw_shop()
        elif self.state == GameState.MENU:
            self._draw_menu()
        
        pygame.display.flip()
    
    def _draw_game(self):
        # Draw zones
        pygame.draw.rect(self.screen, (160, 200, 80), FARM_AREA)
        pygame.draw.rect(self.screen, (140, 180, 60), HORSE_AREA)
        pygame.draw.rect(self.screen, COLOR_BLUE, SELL_ZONE)
        
        # Draw field
        self._draw_field()
        
        # Draw horses
        self._draw_horses()
        
        # Draw manure patches (draw after horses so they're visible)
        for manure in self.manure_patches:
            if hasattr(self, 'manure_img'):
                self.screen.blit(self.manure_img, manure)
            else:
                pygame.draw.circle(self.screen, COLOR_DARK_BROWN, manure.center, 10)
        
        # Draw farmer
        if hasattr(self, 'player_img'):
            self.screen.blit(self.player_img, (self.farmer.x, self.farmer.y))
        else:
            pygame.draw.rect(self.screen, COLOR_BLUE, self.farmer.rect)
        
        # Draw inventory display above player
        self._draw_player_inventory()
        
        # Draw UI
        self._draw_ui()
    
    def _draw_field(self):
        for crop in self.field.crops:
            if crop.growth_stage == 0:  # Seed
                pygame.draw.circle(self.screen, COLOR_BROWN, (int(crop.x), int(crop.y)), 10)
            elif crop.growth_stage == 1:  # Growing
                pygame.draw.circle(self.screen, COLOR_GREEN, (int(crop.x), int(crop.y)), 15)
            elif crop.growth_stage == 2:  # Mature
                # Use crop graphics if available
                if hasattr(self, 'carrot_img') and hasattr(self, 'apple_img') and hasattr(self, 'wheat_img'):
                    if crop.type == CropType.CARROT:
                        self.screen.blit(self.carrot_img, (crop.x - 30, crop.y - 30))
                    elif crop.type == CropType.APPLE:
                        self.screen.blit(self.apple_img, (crop.x - 30, crop.y - 30))
                    else:  # WHEAT
                        self.screen.blit(self.wheat_img, (crop.x - 30, crop.y - 30))
                else:
                    # Fallback to colored circles
                    if crop.type == CropType.CARROT:
                        color = COLOR_ORANGE
                    elif crop.type == CropType.APPLE:
                        color = COLOR_RED
                    else:  # WHEAT
                        color = COLOR_YELLOW
                    pygame.draw.circle(self.screen, color, (int(crop.x), int(crop.y)), 20)
    
    def _draw_horses(self):
        for horse in self.horse_manager.horses:
            # Draw horse body
            if hasattr(self, 'horse_img'):
                self.screen.blit(self.horse_img, (horse.x - 40, horse.y - 30))
            else:
                # Fallback to colored rectangle
                color = COLOR_GREEN
                if horse.state == HorseState.REQUESTING:
                    color = COLOR_YELLOW
                elif horse.state == HorseState.UNHAPPY:
                    color = COLOR_RED
                horse_rect = pygame.Rect(horse.x - 40, horse.y - 30, 80, 60)
                pygame.draw.rect(self.screen, color, horse_rect)
            
            # Draw health bar
            health_pct = horse.health / horse.max_health
            health_bar = pygame.Rect(horse.x - 40, horse.y - 50, 80, 8)
            pygame.draw.rect(self.screen, COLOR_GRAY, health_bar)
            health_fill = pygame.Rect(horse.x - 40, horse.y - 50, int(80 * health_pct), 8)
            pygame.draw.rect(self.screen, COLOR_GREEN, health_fill)
            
            # Draw requests
            if horse.requests and horse.state == HorseState.REQUESTING:
                # Draw multiple food requests using PNG graphics
                for i, request in enumerate(horse.requests):
                    # Position requests horizontally
                    request_x = horse.x - 20 + (i * 25)
                    request_y = horse.y - 70
                    
                    # Use mini PNG graphics if available
                    if hasattr(self, 'mini_carrot_img') and hasattr(self, 'mini_apple_img') and hasattr(self, 'mini_wheat_img'):
                        if request == CropType.CARROT:
                            self.screen.blit(self.mini_carrot_img, (request_x, request_y))
                        elif request == CropType.APPLE:
                            self.screen.blit(self.mini_apple_img, (request_x, request_y))
                        else:  # WHEAT
                            self.screen.blit(self.mini_wheat_img, (request_x, request_y))
                    else:
                        # Fallback to colored circles
                        if request == CropType.CARROT:
                            request_color = COLOR_ORANGE
                        elif request == CropType.APPLE:
                            request_color = COLOR_RED
                        else:  # WHEAT
                            request_color = COLOR_YELLOW
                        pygame.draw.circle(self.screen, request_color, (request_x + 8, request_y + 8), 8)
                
                # Draw progress
                progress_text = self.small_font.render(f"{horse.fed_amount}/{len(horse.requests) + horse.fed_amount}", True, COLOR_BLACK)
                self.screen.blit(progress_text, (horse.x - 20, horse.y - 90))
                
                # Draw timer
                timer_text = self.small_font.render(f"{horse.request_timer:.1f}s", True, COLOR_BLACK)
                self.screen.blit(timer_text, (horse.x - 20, horse.y - 110))
    
    def _draw_player_inventory(self):
        # Draw inventory items above player's head
        inv_x = self.farmer.x
        inv_y = self.farmer.y - 25
        item_spacing = 18
        
        # Draw crops
        for crop_type, count in self.farmer.inventory.items():
            if crop_type in [CropType.CARROT, CropType.APPLE, CropType.WHEAT]:
                for i in range(count):
                    if hasattr(self, 'mini_carrot_img') and hasattr(self, 'mini_apple_img') and hasattr(self, 'mini_wheat_img'):
                        if crop_type == CropType.CARROT:
                            self.screen.blit(self.mini_carrot_img, (inv_x + i * item_spacing, inv_y))
                        elif crop_type == CropType.APPLE:
                            self.screen.blit(self.mini_apple_img, (inv_x + i * item_spacing, inv_y))
                        else:  # WHEAT
                            self.screen.blit(self.mini_wheat_img, (inv_x + i * item_spacing, inv_y))
                    else:
                        # Fallback to colored circles
                        if crop_type == CropType.CARROT:
                            color = COLOR_ORANGE
                        elif crop_type == CropType.APPLE:
                            color = COLOR_RED
                        else:  # WHEAT
                            color = COLOR_YELLOW
                        pygame.draw.circle(self.screen, color, (inv_x + i * item_spacing + 8, inv_y + 8), 6)
        
        # Draw manure (if any)
        if 'manure' in self.farmer.inventory and self.farmer.inventory['manure'] > 0:
            manure_count = self.farmer.inventory['manure']
            crop_count = sum(count for crop_type, count in self.farmer.inventory.items() if crop_type in [CropType.CARROT, CropType.APPLE, CropType.WHEAT])
            
            for i in range(manure_count):
                if hasattr(self, 'mini_manure_img'):
                    self.screen.blit(self.mini_manure_img, (inv_x + (crop_count + i) * item_spacing, inv_y))
                else:
                    pygame.draw.circle(self.screen, COLOR_DARK_BROWN, (inv_x + (crop_count + i) * item_spacing + 8, inv_y + 8), 6)
    
    def _draw_ui(self):
        # Draw inventory
        inv_y = 10
        crop_order = [CropType.CARROT, CropType.APPLE, CropType.WHEAT]
        crop_names = {'carrot': '🥕', 'apple': '🍎', 'wheat': '🌾'}
        
        for crop_type in crop_order:
            count = self.farmer.inventory.get(crop_type, 0)
            if count > 0:
                text = self.small_font.render(f"{crop_names[crop_type.value]}: {count}", True, COLOR_BLACK)
                self.screen.blit(text, (10, inv_y))
                inv_y += 25
        
        # Draw money
        money_text = self.font.render(f"Money: ${self.farmer.money}", True, COLOR_BLACK)
        self.screen.blit(money_text, (10, inv_y + 10))
        
        # Draw level and feedings
        level_text = self.small_font.render(f"Level {self.current_level} | Feedings: {self.total_feedings}", True, COLOR_BLACK)
        self.screen.blit(level_text, (10, inv_y + 50))
        
        # Draw sell zone label
        sell_text = self.small_font.render("SELL MANURE", True, COLOR_WHITE)
        self.screen.blit(sell_text, (SELL_ZONE.x + 10, SELL_ZONE.y + 20))
    
    def _draw_shop(self):
        # Draw shop background
        shop_rect = pygame.Rect(SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 150, 400, 300)
        pygame.draw.rect(self.screen, COLOR_WHITE, shop_rect)
        pygame.draw.rect(self.screen, COLOR_BLACK, shop_rect, 3)
        
        # Title
        title = self.font.render("SHOP - Press P to Close", True, COLOR_BLACK)
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 120))
        self.screen.blit(title, title_rect)
        
        # Money display
        money_text = self.font.render(f"Money: ${self.farmer.money}", True, COLOR_BLACK)
        money_rect = money_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 80))
        self.screen.blit(money_text, money_rect)
        
        # Draw upgrades
        upgrade_info = [
            ('1', 'carry'), ('2', 'speed'), 
            ('3', 'carrot_plot'), ('4', 'apple_plot'), ('5', 'wheat_plot')
        ]
        
        for key, upgrade_key in upgrade_info:
            upgrade = self.upgrades[upgrade_key]
            
            # Determine color based on affordability and level
            if upgrade['level'] >= upgrade['max_level']:
                color = COLOR_GRAY
                status = f"MAX ({upgrade['level']})"
            elif self.farmer.money >= upgrade['cost']:
                color = COLOR_GREEN
                status = f"${upgrade['cost']} (Lvl {upgrade['level']})"
            else:
                color = COLOR_RED
                status = f"${upgrade['cost']} (Lvl {upgrade['level']})"
            
            # Draw upgrade box
            y_pos = SCREEN_HEIGHT//2 - 30 + upgrade_info.index((key, upgrade_key)) * 50
            upgrade_rect = pygame.Rect(SCREEN_WIDTH//2 - 180, y_pos, 360, 45)
            pygame.draw.rect(self.screen, color, upgrade_rect, 2)
            
            # Draw upgrade text
            key_text = self.small_font.render(f"[{key}]", True, COLOR_BLACK)
            self.screen.blit(key_text, (upgrade_rect.x + 5, upgrade_rect.y + 2))
            
            name_text = self.small_font.render(upgrade['name'], True, COLOR_BLACK)
            self.screen.blit(name_text, (upgrade_rect.x + 30, upgrade_rect.y + 2))
            
            desc_text = self.small_font.render(upgrade['description'], True, COLOR_BLACK)
            self.screen.blit(desc_text, (upgrade_rect.x + 10, upgrade_rect.y + 20))
            
            # Draw price/status
            price_text = self.small_font.render(status, True, color)
            self.screen.blit(price_text, (upgrade_rect.x + 10, upgrade_rect.y + 35))
    
    def _draw_menu(self):
        title = self.font.render("Farmer's Harvest", True, COLOR_BLACK)
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, 200))
        self.screen.blit(title, title_rect)
        
        start = self.small_font.render("Press SPACE to Start | ESC to Quit", True, COLOR_BLACK)
        start_rect = start.get_rect(center=(SCREEN_WIDTH//2, 300))
        self.screen.blit(start, start_rect)
    
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            
            self.handle_events()
            self.update(dt)
            self.draw()
        
        pygame.quit()
        sys.exit()

# ============ MAIN ============
if __name__ == "__main__":
    game = Game()
    game.run()
