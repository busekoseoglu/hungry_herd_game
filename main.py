import pygame
import sys
import random
import math
import os
from enum import Enum
from dataclasses import dataclass
from typing import List

# ============ BAŞLATMA ============
pygame.init()

# ============ AYARLAR ============
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 700
FPS = 60

# Renkler
COLOR_GRASS = (180, 220, 100)  # Açık yeşil
COLOR_BROWN = (139, 69, 19)
COLOR_DARK_BROWN = (101, 50, 15)
COLOR_ORANGE = (255, 165, 0)      # Havuç rengi
COLOR_RED = (220, 20, 60)        # Elma rengi (koyu kırmızı)
# Soluk/pale tonlar (istek gösterimi için)
COLOR_PALE_ORANGE = (255, 210, 150)
COLOR_PALE_RED = (255, 180, 180)
COLOR_YELLOW = (255, 255, 0)
COLOR_GREEN = (0, 200, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GRAY = (128, 128, 128)

# Spacing constant used for food icons near horses
ThirtyFiveSpacing = 45

# Bölgeler
FARM_END = 350           # Tarlanın sağ sınırı (sol taraf)
HORSES_START = SCREEN_WIDTH - 180  # Atlar bölgesinin başlangıcı (sağ taraf)

# ============ ENUMS ============
class FoodType(Enum):
    APPLE = 0        # Elma
    CARROT = 1       # Havuç

class HorseState(Enum):
    WAITING = 0      # Yeşil - Bekliyor
    HUNGRY = 1       # Sarı - Aç (timer çalışıyor)
    CRITICAL = 2     # Kırmızı - Ölmek üzere (son %20)
    DEAD = 3         # Siyah - Ölü
    FED = 4          # Yeşil pulse - Başarıyla beslenmiş (çıkacak)

class PlayerState(Enum):
    EMPTY = 0        # Eli boş
    CARRYING_SEED = 1     # Tohum taşıyor
    CARRYING_CARROT = 2   # Havuç/Elma taşıyor

class CropState(Enum):
    SEED = 0         # Tohum (henüz ekilmiş)
    GROWING = 1      # Büyüyor
    MATURE = 2       # Hasat hazır

# ============ SINIFLARI ============
@dataclass
class Food:
    """Besin sistemi"""
    x: float
    y: float
    food_type: FoodType
    
    def draw(self, screen):
        # Elma: Yuvarlak (koyu kırmızı), Havuç: Dikdörtgen (turuncu)
        if self.food_type == FoodType.APPLE:
            color = COLOR_RED
            # ELMA → YUVARLAK
            pygame.draw.circle(screen, color, (int(self.x), int(self.y)), 10)
            pygame.draw.circle(screen, COLOR_DARK_BROWN, (int(self.x), int(self.y)), 10, 2)
        else:  # CARROT
            color = COLOR_ORANGE
            # HAVUÇ → DİKDÖRTGEN
            rect_width = 16
            rect_height = 20
            rect_x = self.x - rect_width // 2
            rect_y = self.y - rect_height // 2
            pygame.draw.rect(screen, color, (int(rect_x), int(rect_y), rect_width, rect_height))
            pygame.draw.rect(screen, COLOR_DARK_BROWN, (int(rect_x), int(rect_y), rect_width, rect_height), 2)

class Crop:
    """Ekili bitki (şu an sadece havuç)"""
    GROWTH_TIME = 3.0  # 3 saniyede tamamlanır
    
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.state = CropState.SEED
        self.elapsed_time = 0.0
        self.food_type = FoodType.CARROT  # Şu an sadece havuç ekiyoruz
        
    def update(self, dt):
        """Bitkiyi güncelle"""
        if self.state == CropState.SEED:
            self.elapsed_time += dt
            if self.elapsed_time >= self.GROWTH_TIME:
                self.state = CropState.MATURE
    
    def get_growth_percentage(self) -> float:
        """0.0 (tohum) - 1.0 (yetişkin) arasında büyüme yüzdesi"""
        if self.state == CropState.SEED:
            return self.elapsed_time / self.GROWTH_TIME
        return 1.0 if self.state == CropState.MATURE else 0.0
    
    def draw(self, screen, sprites=None):
        """Bitkiyi çiz"""
        if self.state == CropState.MATURE:
            # Yetişkin havuç - crop_mature sprite (1.5x daha büyük)
            if sprites and sprites.get('crop_mature'):
                spr = sprites['crop_mature']
                sw, sh = spr.get_size()
                # 1.5x ölçeklendir
                scaled_w = int(sw * 1.5)
                scaled_h = int(sh * 1.5)
                scaled_spr = pygame.transform.smoothscale(spr, (scaled_w, scaled_h))
                screen.blit(scaled_spr, (int(self.x - scaled_w//2), int(self.y - scaled_h//2)))
            else:
                pygame.draw.rect(screen, COLOR_ORANGE, (int(self.x - 12), int(self.y - 15), 24, 30))
                pygame.draw.rect(screen, COLOR_BLACK, (int(self.x - 12), int(self.y - 15), 24, 30), 1)
        else:
            # Tohum - crop_seed sprite
            if sprites and sprites.get('crop_seed'):
                spr = sprites['crop_seed']
                growth = self.get_growth_percentage()
                # Boyutu büyümeye göre ölçeklendir
                base_w, base_h = spr.get_size()
                new_w = max(2, int(base_w * growth))
                new_h = max(2, int(base_h * growth))
                if new_w > 0 and new_h > 0:
                    scaled = pygame.transform.smoothscale(spr, (new_w, new_h))
                    screen.blit(scaled, (int(self.x - new_w//2), int(self.y - new_h//2)))
            else:
                growth = self.get_growth_percentage()
                size = max(2, int(8 * growth))
                pygame.draw.circle(screen, COLOR_ORANGE, (int(self.x), int(self.y)), size)
                pygame.draw.circle(screen, COLOR_BLACK, (int(self.x), int(self.y)), size, 1)

class Horse:
    """At sınıfı - Task management gibi"""
    SPAWN_TIMES = [45, 42, 40, 36, 34]  # Zorluk katsayısı - zaman kısalır (uzatıldı)
    
    # Mümkün besin kombinasyonları
    FOOD_RECIPES = [
        [FoodType.APPLE, FoodType.CARROT],
        [FoodType.CARROT, FoodType.CARROT, FoodType.APPLE],
        [FoodType.APPLE, FoodType.APPLE, FoodType.CARROT],
    ]
    
    # Level 1 tarifi - sadece havuç
    FOOD_RECIPES_LEVEL1 = [
        [FoodType.CARROT],
        [FoodType.CARROT, FoodType.CARROT],
        [FoodType.CARROT],
    ]
    
    def __init__(self, spawn_index: int, level: int = 1):
        self.spawn_index = min(spawn_index, len(self.SPAWN_TIMES) - 1)
        self.x = HORSES_START + 50
        # Aralarına ekstra boşluk ekleyerek görünümü daha ferah hale getir
        self.y = 80 + spawn_index * 200  # Atların arasını daha açık yap (150→180→200)
        self.width = 60
        self.height = 50
        # assign preferred sprite name (if available in assets)
        self.horse_sprite_name = 'horse'  # Sabit isimle horse.png yükle
        
        # State
        self.state = HorseState.WAITING
        # Level'e göre başlangıç zamanını ayarla (Level 1 daha uzun)
        base_time = self.SPAWN_TIMES[self.spawn_index]
        self.remaining_time = base_time * (1.5 if level == 1 else 1.0)
        self.max_time = self.remaining_time
        
        # Besin sistemi - her at farklı besin kombinasyonu ister
        recipes = self.FOOD_RECIPES_LEVEL1 if level == 1 else self.FOOD_RECIPES
        self.required_foods = recipes[spawn_index % len(recipes)].copy()
        # current_foods is a slot list aligned to required_foods; None means unfilled
        self.current_foods: list = [None] * len(self.required_foods)
        
        self.fed_count = 0
        self.fed_animation_timer = 0  # Fed olduğunda animasyon için
        # Pulsing animation when fed
        self.pulsing = False
        self.pulse_timer = 0.0
        self.pulse_duration = 0.8
        # Time bonus visual
        self.time_bonus_timer = 0.0
        self.time_bonus_amount = 0
        self.level = level
        self.last_food_count = len(self.required_foods)  # Başlangıç sayısı
        
    def update(self, dt):
        """Her frame güncelle"""
        if self.state == HorseState.DEAD:
            return

        # Pulsing timer update
        if self.pulsing:
            self.pulse_timer += dt
            if self.pulse_timer >= self.pulse_duration:
                self.pulsing = False

        # Time bonus timer update
        if self.time_bonus_timer > 0:
            self.time_bonus_timer -= dt
            if self.time_bonus_timer < 0:
                self.time_bonus_timer = 0

        # Eğer bekliyorsa aç hale geç
        if self.state == HorseState.WAITING:
            self.state = HorseState.HUNGRY

        if self.state == HorseState.HUNGRY or self.state == HorseState.CRITICAL:
            self.remaining_time -= dt

            # Timerı kontrol et
            time_percent = self.remaining_time / self.max_time
            if time_percent < 0.2:
                self.state = HorseState.CRITICAL

            # Ölmek üzere
            if self.remaining_time <= 0:
                self.state = HorseState.DEAD
                self.remaining_time = 0
    
    def receive_food(self, food_type: FoodType):
        """Oyuncudan besin al

        - Eşleşen ilk boş slota yerleştir (soldan sağa)
        - Eğer aynı tür için boş slot yoksa ceza uygula
        - Doğru parça verildiyse zaman bonusu ver
        """
        if self.state == HorseState.DEAD:
            return False

        # Kaç tane bu tip zaten verildi
        have_count = self.current_foods.count(food_type)
        need_count = self.required_foods.count(food_type)

        # Eğer bu tip zaten yeterince verildiyse -> yanlış/boşa verme -> ceza
        if have_count >= need_count:
            self.remaining_time = max(0, self.remaining_time - 2)
            return False

        # Bulunacak ilk uygun slot indexini bul
        slot_index = None
        for idx, req in enumerate(self.required_foods):
            if req == food_type and self.current_foods[idx] is None:
                slot_index = idx
                break

        if slot_index is None:
            # Hatayla eşleşen slot yok -> ceza
            self.remaining_time = max(0, self.remaining_time - 2)
            return False

        # Slotu doldur
        self.current_foods[slot_index] = food_type
        self.fed_count += 1

        # Küçük zaman bonusu (ör. +4s), maksimum max_time'ı aşma
        bonus = 4
        self.remaining_time = min(self.max_time, self.remaining_time + bonus)
        self.time_bonus_timer = 1.2
        self.time_bonus_amount = bonus

        # Eğer hepsi verildiyse kontrol et (tüm slotlar doluysa)
        if all(x is not None for x in self.current_foods):
            # Doğru kombinasyon verildiğini kontrol et (zorunlu eşleşme zaten sağlanmış olmalı)
            if sorted([f.value for f in self.current_foods]) == sorted([f.value for f in self.required_foods]):
                # Başarıyla beslendi -> yeni istekle devam et
                self.on_successful_feed()
                return True
            else:
                # Yanlış kombinasyon verildiyse küçük bir ceza uygula
                self.remaining_time = max(0, self.remaining_time - 3)
                return False

        return False
    
    def is_alive(self):
        return self.state not in [HorseState.DEAD]
    
    def get_remaining_foods(self):
        """Kalan besin ihtiyacını hesapla"""
        remaining = sum(1 for x in self.current_foods if x is None)
        return max(0, remaining)

    def on_successful_feed(self):
        """At başarıyla beslendiğinde yeni istek üret ve timerı resetle"""
        self.fed_count += 1
        # Görsel feedback: pulsing
        self.pulsing = True
        self.pulse_timer = 0.0
        # Yeni istek oluştur: beslendikçe istenen havuç sayısını değiştir
        if self.level == 1:
            # Level 1: yalnızca havuç istiyor — rastgele 1-3 arası, öncekiyle aynı olmasın
            previous_count = self.last_food_count
            while True:
                new_count = random.choice([1, 2, 3])
                if new_count != previous_count:
                    break
            self.required_foods = [FoodType.CARROT for _ in range(new_count)]
            self.last_food_count = new_count
        else:
            # Level >1: karışık istekler, uzunluk 1-4, karışık elma/havuç
            new_len = random.randint(1, 4)
            self.required_foods = [random.choice([FoodType.CARROT, FoodType.APPLE]) for _ in range(new_len)]

        self.current_foods = [None] * len(self.required_foods)
        # Zorluk: beslendikçe biraz daha kısa sürede tekrar istek olabilir
        self.max_time = max(12, self.max_time - 1)
        self.remaining_time = self.max_time
        self.state = HorseState.WAITING
    
    def draw(self, screen, sprites):
        if not self.is_alive():
            return

        # If a sprite exists for this horse, blit it first (centered)
        horse_sprite = sprites.get(self.horse_sprite_name)
        if horse_sprite:
            spr = horse_sprite
            sw, sh = spr.get_size()
            # scale to approximate height target (128px) while keeping aspect
            target_h = 128
            scale = target_h / sh if sh > 0 else 1.0
            new_w = int(sw * scale)
            new_h = int(sh * scale)
            spr_scaled = pygame.transform.smoothscale(spr, (new_w, new_h))
            blit_x = int(self.x + self.width/2 - new_w/2)
            blit_y = int(self.y + self.height/2 - new_h/2)
            screen.blit(spr_scaled, (blit_x, blit_y))
        else:
            # Pulse animasyonu FED state'inde
            alpha = 1.0
            if self.state == HorseState.FED:
                # Pulsing effect
                alpha = 0.5 + 0.5 * (0.5 * (1 + __import__('math').sin(self.fed_animation_timer * 10)))

            # Pulsing halo if recently fed
            if self.pulsing:
                # Create a temporary surface with alpha
                scale = 1.0 + 0.4 * math.sin(self.pulse_timer * 10)
                halo_w = int(self.width * 2.0 * scale)
                halo_h = int(self.height * 1.8 * scale)
                surf = pygame.Surface((halo_w, halo_h), pygame.SRCALPHA)
                alpha = int(160 * max(0.2, 1.0 - (self.pulse_timer / self.pulse_duration)))
                pygame.draw.ellipse(surf, (255, 210, 120, alpha), (0, 0, halo_w, halo_h))
                blit_x = int(self.x + self.width/2 - halo_w/2)
                blit_y = int(self.y + self.height/2 - halo_h/2)
                screen.blit(surf, (blit_x, blit_y))

            # At gövdesi (basit)
            pygame.draw.ellipse(screen, COLOR_BROWN, (self.x, self.y, self.width, self.height))
            
            # Baş
            pygame.draw.circle(screen, COLOR_DARK_BROWN, (int(self.x + self.width), int(self.y + 15)), 10)
            
            # Kulaklar
            pygame.draw.polygon(screen, COLOR_DARK_BROWN, [
                (self.x + self.width + 5, self.y),
                (self.x + self.width + 8, self.y - 8),
                (self.x + self.width + 12, self.y)
            ])

        # Timer bar (AT KAFASININ ÜSTÜNDEKİ BAR)
        bar_width = 80
        bar_height = 10
        bar_x = self.x - 5
        bar_y = self.y - 40  # Kafanın üstüne taşı (-25→-40)

        # Arka plan (siyah)
        pygame.draw.rect(screen, COLOR_BLACK, (bar_x, bar_y, bar_width, bar_height))

        # Dolu kısmı
        filled_width = bar_width * max(0, self.remaining_time / self.max_time)

        # Renk: Yeşil → Sarı → Kırmızı
        time_percent = max(0, self.remaining_time / self.max_time)
        if time_percent > 0.5:
            color = COLOR_GREEN
        elif time_percent > 0.2:
            color = COLOR_YELLOW
        else:
            color = COLOR_RED

        pygame.draw.rect(screen, color, (bar_x, bar_y, filled_width, bar_height))
        pygame.draw.rect(screen, COLOR_WHITE, (bar_x, bar_y, bar_width, bar_height), 2)

        # Time bonus text
        if self.time_bonus_timer > 0:
            font = pygame.font.Font(None, 20)
            txt = f"+{int(self.time_bonus_amount)}s"
            text_surf = font.render(txt, True, COLOR_GREEN)
            text_rect = text_surf.get_rect(center=(self.x + bar_width//2, bar_y - 12))
            screen.blit(text_surf, text_rect)

        # Besin göstergesi (AT ÖNÜ) - Havuç sprite'ı, soluk/parlak opacity
        # Besin ikonlarının atla aynı hizada olsun
        circles_y = self.y + 25  # Atın merkezinde konumlandır
        for i in range(len(self.required_foods)):
            # başlangıçta daha sola kaydır; aralarına ekstra boşluk ekle
            circle_x = self.x - 150 + i *  ThirtyFiveSpacing  # Atın solunda daha uzak konumlandır

            # Bu konuma hangi besin gelecek?
            required_food_type = self.required_foods[i]

            # Bu konumda besin alındı mı? (slot kontrolü)
            received = (self.current_foods[i] is not None)

            # Havuç sprite'ı kullan (carrot.png)
            if required_food_type == FoodType.CARROT and sprites and sprites.get('carrot'):
                carrot_sprite = sprites['carrot']
                sw, sh = carrot_sprite.get_size()
                
                # 1.5x daha büyük göster
                scaled_w = int(sw * 1.5)
                scaled_h = int(sh * 1.5)
                
                # Opacity: Beslenmediyse soluk (120), beslenmediyse parlak turuncu (255)
                if received:
                    alpha = 255  # Parlak - beslenmiş
                else:
                    alpha = 120  # Soluk - aç, ihtiyaç duyuyor
                
                # Sprite'ı alpha ile çiz
                temp_surf = carrot_sprite.copy()
                temp_surf.set_alpha(alpha)
                scaled = pygame.transform.smoothscale(temp_surf, (scaled_w, scaled_h))
                screen.blit(scaled, (int(circle_x - scaled_w//2), int(circles_y - scaled_h//2)))
            elif required_food_type == FoodType.APPLE:
                # ELMA → YUVARLAK (eski sistem)
                if received:
                    color = COLOR_RED  # Koyu kırmızı - elma verildi
                else:
                    color = COLOR_PALE_RED  # Soluk kırmızı - elma isteniyor
                pygame.draw.circle(screen, color, (int(circle_x), int(circles_y)), 8)
                pygame.draw.circle(screen, COLOR_BLACK, (int(circle_x), int(circles_y)), 8, 2)

class Player:
    """Oyuncu - At bakıcısı"""
    def __init__(self):
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT // 2
        self.width = 40
        self.height = 50
        self.speed = 300  # pixels/second
        self.state = PlayerState.EMPTY
        self.carrying_item = None  # "SEED", "CARROT" veya "APPLE"
        self.seed_count = 0  # Taşıdığı tohum sayısı (max 5)
        
    def update(self, keys, dt):
        """Oyuncu kontrolleri"""
        dx = 0
        dy = 0
        
        if keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_s]:
            dy += 1
        if keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_d]:
            dx += 1
        
        # Normalleştir
        if dx != 0 or dy != 0:
            length = (dx**2 + dy**2) ** 0.5
            dx /= length
            dy /= length
        
        # Pozisyon güncelle
        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt
        
        # Sınırları kontrol et
        self.x = max(0, min(self.x, HORSES_START))
        self.y = max(50, min(self.y, SCREEN_HEIGHT - 50))
    
    def pick_seed(self) -> bool:
        """Depodan tohum al (max 5)"""
        if self.state == PlayerState.EMPTY and self.seed_count < 5:
            self.seed_count += 1
            self.state = PlayerState.CARRYING_SEED
            self.carrying_item = "SEED"
            return True
        return False
    
    def harvest_carrot(self) -> bool:
        """Yetişkin bitkiden havuç hasat et"""
        if self.state == PlayerState.EMPTY:
            self.state = PlayerState.CARRYING_CARROT
            self.carrying_item = "CARROT"
            return True
        return False
    
    def pick_apple(self) -> bool:
        """Elmayı al"""
        if self.state == PlayerState.EMPTY:
            self.state = PlayerState.CARRYING_CARROT
            self.carrying_item = "APPLE"
            return True
        return False
    
    def feed_horse(self, horse: Horse) -> bool:
        """Ata besin ver"""
        if self.state == PlayerState.CARRYING_CARROT and self.carrying_item == "CARROT":
            # Oyuncu at bölgesindeyse havuç ver
            distance = ((self.x - horse.x)**2 + (self.y - horse.y)**2) ** 0.5
            if distance < 80 and horse.is_alive():
                result = horse.receive_food(FoodType.CARROT)
                # Havuç verdikten sonra, eli boşalt
                self.state = PlayerState.EMPTY
                self.carrying_item = None
                return result
        return False
    
    def use_stored_food(self, food_type: FoodType) -> bool:
        """Depodaki besini al ve taşı"""
        if self.state == PlayerState.EMPTY:
            if food_type == FoodType.CARROT and self.inventory_carrot > 0:
                self.inventory_carrot -= 1
                self.state = PlayerState.CARRYING
                self.carrying_food_type = food_type
                return True
        return False
    
    def draw(self, screen, sprites):
        """Oyuncu çiz - sprite varsa onu kullanalım, yoksa üçgen"""
        sprite = sprites.get('player_extracted') or sprites.get('player')
        if sprite:
            sw, sh = sprite.get_size()
            target_h = 80
            scale = target_h / sh if sh > 0 else 1.0
            new_w = int(sw * scale)
            new_h = int(sh * scale)
            spr_scaled = pygame.transform.smoothscale(sprite, (new_w, new_h))
            blit_x = int(self.x - new_w//2)
            blit_y = int(self.y - new_h//2)
            screen.blit(spr_scaled, (blit_x, blit_y))
        else:
            # Üçgen
            points = [
                (self.x, self.y - self.height // 2),  # Üst
                (self.x - self.width // 2, self.y + self.height // 2),  # Sol alt
                (self.x + self.width // 2, self.y + self.height // 2)  # Sağ alt
            ]
            color = COLOR_ORANGE if self.state in [PlayerState.CARRYING_SEED, PlayerState.CARRYING_CARROT] else COLOR_GREEN
            pygame.draw.polygon(screen, color, points)
            pygame.draw.polygon(screen, COLOR_BLACK, points, 2)

        # Taşıdığı öğeyi göster
        if self.state == PlayerState.CARRYING_SEED and self.carrying_item == "SEED":
            # Tohum göster (crop_seed sprite) - büyütülmüş
            food_y = self.y - 10
            seed_sprite = sprites.get('crop_seed')
            if seed_sprite:
                sw, sh = seed_sprite.get_size()
                # 2x büyütülü göster
                scaled_seed = pygame.transform.smoothscale(seed_sprite, (sw*2, sh*2))
                screen.blit(scaled_seed, (int(self.x - sw//2 * 2), int(food_y - sh//2 * 2)))
            else:
                pygame.draw.circle(screen, COLOR_GREEN, (int(self.x), int(food_y)), 6)
                pygame.draw.circle(screen, COLOR_BLACK, (int(self.x), int(food_y)), 6, 1)
        elif self.state == PlayerState.CARRYING_CARROT:
            food_y = self.y - 10
            if self.carrying_item == "CARROT":
                # Havuç göster (carrot sprite) - büyütülmüş
                carrot_sprite = sprites.get('carrot')
                if carrot_sprite:
                    sw, sh = carrot_sprite.get_size()
                    # 2x büyütülü göster
                    scaled_carrot = pygame.transform.smoothscale(carrot_sprite, (sw*2, sh*2))
                    screen.blit(scaled_carrot, (int(self.x - sw * 2 // 2), int(food_y - sh * 2 // 2)))
                else:
                    rect_width = 12
                    rect_height = 16
                    rect_x = self.x - rect_width // 2
                    rect_y = food_y - rect_height // 2
                    pygame.draw.rect(screen, COLOR_ORANGE, (int(rect_x), int(rect_y), rect_width, rect_height))
                    pygame.draw.rect(screen, COLOR_BLACK, (int(rect_x), int(rect_y), rect_width, rect_height), 1)
            elif self.carrying_item == "APPLE":
                # Elma göster
                apple_sprite = sprites.get('apple')
                if apple_sprite:
                    sw, sh = apple_sprite.get_size()
                    screen.blit(apple_sprite, (int(self.x - sw//2), int(food_y - sh//2)))
                else:
                    pygame.draw.circle(screen, COLOR_RED, (int(self.x), int(food_y)), 8)
                    pygame.draw.circle(screen, COLOR_BLACK, (int(self.x), int(food_y)), 8, 1)

class Game:
    """Ana oyun sınıfı"""
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Feed the Herd")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 48)
        self.font_huge = pygame.font.Font(None, 72)
        
        # Tuş durumu takibi (tek seferlik tuş basışları için)
        self.prev_e_pressed = False

        # --- Load pixel-art assets from `assets/` if available, otherwise generate them; fallback to procedural ---
        assets_dir = os.path.join(os.path.dirname(__file__), 'assets')

        def load_asset(name):
            path = os.path.join(assets_dir, f"{name}.png")
            try:
                surf = pygame.image.load(path).convert_alpha()
                return surf
            except Exception as e:
                print(f"Failed to load {name}.png: {e}")
                return None
        
        def scale_asset(surf, target_size):
            """Sprite'ı verilen boyuta ölçeklendir"""
            if surf is None:
                return None
            return pygame.transform.smoothscale(surf, target_size)

        required = ['horse', 'player', 'apple', 'apple_pale', 'carrot', 'carrot_pale',
                    'crop_seed', 'crop_mature', 'bg_farm', 'bg_grass', 'bg_horses']

        # If any asset missing, attempt to generate them
        missing = any(not os.path.exists(os.path.join(assets_dir, f"{r}.png")) for r in required)
        if missing:
            try:
                import assets.generate_assets as gen
                gen.generate(assets_dir)
            except Exception as e:
                print("Asset generation failed:", e)

        # Try to load assets
        self.sprites = {}
        for name in required:
            surf = load_asset(name)
            self.sprites[name] = surf
        
        # Yüklenen sprite'ları doğru boyuta ölçeklendir
        target_sizes = {
            'player': (36, 44),
            'carrot': (20, 24),
            'carrot_pale': (20, 24),
            'crop_seed': (16, 16),
            'crop_mature': (20, 24),
            'apple': (20, 20),
            'apple_pale': (20, 20),
            'horse': (100, 60)
        }
        
        for name, target_size in target_sizes.items():
            if self.sprites.get(name) is not None:
                surf = self.sprites[name]
                scaled = pygame.transform.smoothscale(surf, target_size)
                self.sprites[name] = scaled

        # If some assets are still missing, create them procedurally only for missing ones
        def make_surface(w, h):
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            return s

        # Horse
        if self.sprites.get('horse') is None:
            horse_surf = make_surface(100, 60)
            pygame.draw.ellipse(horse_surf, COLOR_BROWN, (0, 12, 80, 38))
            pygame.draw.circle(horse_surf, COLOR_DARK_BROWN, (72, 20), 12)
            pygame.draw.polygon(horse_surf, COLOR_DARK_BROWN, [(74, 10), (92, 6), (82, 24)])
            self.sprites['horse'] = horse_surf

        # Player sprite (triangle)
        if self.sprites.get('player') is None:
            player_surf = make_surface(36, 44)
            pygame.draw.polygon(player_surf, COLOR_GREEN, [(18, 2), (2, 40), (34, 40)])
            pygame.draw.polygon(player_surf, COLOR_BLACK, [(18, 2), (2, 40), (34, 40)], 2)
            self.sprites['player'] = player_surf

        # Apple sprites
        if self.sprites.get('apple') is None:
            apple = make_surface(20, 20)
            pygame.draw.circle(apple, COLOR_RED, (10, 10), 8)
            pygame.draw.circle(apple, COLOR_BLACK, (10, 10), 8, 1)
            self.sprites['apple'] = apple
        if self.sprites.get('apple_pale') is None:
            apple_pale = make_surface(20, 20)
            pygame.draw.circle(apple_pale, COLOR_PALE_RED, (10, 10), 8)
            pygame.draw.circle(apple_pale, COLOR_BLACK, (10, 10), 8, 1)
            self.sprites['apple_pale'] = apple_pale

        # Carrot sprites
        if self.sprites.get('carrot') is None:
            carrot = make_surface(20, 24)
            pygame.draw.rect(carrot, COLOR_ORANGE, (4, 3, 12, 18))
            pygame.draw.rect(carrot, COLOR_BLACK, (4, 3, 12, 18), 1)
            self.sprites['carrot'] = carrot
        if self.sprites.get('carrot_pale') is None:
            carrot_pale = make_surface(20, 24)
            pygame.draw.rect(carrot_pale, COLOR_PALE_ORANGE, (4, 3, 12, 18))
            pygame.draw.rect(carrot_pale, COLOR_BLACK, (4, 3, 12, 18), 1)
            self.sprites['carrot_pale'] = carrot_pale

        # Crop sprites
        if self.sprites.get('crop_seed') is None:
            crop_seed = make_surface(16, 16)
            pygame.draw.circle(crop_seed, COLOR_GREEN, (8, 8), 4)
            pygame.draw.circle(crop_seed, COLOR_BLACK, (8, 8), 4, 1)
            self.sprites['crop_seed'] = crop_seed
        if self.sprites.get('crop_mature') is None:
            crop_mature = make_surface(20, 24)
            pygame.draw.rect(crop_mature, COLOR_ORANGE, (4, 6, 12, 16))
            pygame.draw.rect(crop_mature, COLOR_BLACK, (4, 6, 12, 16), 1)
            self.sprites['crop_mature'] = crop_mature
        # Backgrounds
        if self.sprites.get('bg_farm') is None:
            farm_bg = make_surface(FARM_END, SCREEN_HEIGHT)
            farm_bg.fill((139, 90, 43))
            for i in range(0, FARM_END, 20):
                pygame.draw.line(farm_bg, (120, 70, 30), (i, 0), (i, SCREEN_HEIGHT), 1)
            for j in range(0, SCREEN_HEIGHT, 20):
                pygame.draw.line(farm_bg, (120, 70, 30), (0, j), (FARM_END, j), 1)
            self.sprites['bg_farm'] = farm_bg

        if self.sprites.get('bg_grass') is None:
            grass_bg = make_surface(HORSES_START - FARM_END, SCREEN_HEIGHT)
            grass_bg.fill(COLOR_GRASS)
            self.sprites['bg_grass'] = grass_bg

        if self.sprites.get('bg_horses') is None:
            horses_bg = make_surface(SCREEN_WIDTH - HORSES_START, SCREEN_HEIGHT)
            horses_bg.fill((200, 220, 150))
            self.sprites['bg_horses'] = horses_bg

        # Eğer bazı sprite'lar eksikti ve biz procedural olarak oluşturdumuzsa,
        # bunları `assets/` dizinine PNG olarak kaydetmeye çalışalım
        try:
            os.makedirs(assets_dir, exist_ok=True)
            for name, surf in self.sprites.items():
                if surf is None:
                    continue
                path = os.path.join(assets_dir, f"{name}.png")
                # Eğer dosya yoksa kaydet
                if not os.path.exists(path):
                    try:
                        pygame.image.save(surf, path)
                    except Exception as e:
                        print(f"Failed to save {name}.png: {e}")
        except Exception as e:
            print("Failed to persist generated assets:", e)

        self.reset_game()
    
    def reset_game(self):
        self.player = Player()
        self.horses: List[Horse] = []
        self.crops: List[Crop] = []  # Ekili bitkiler
        
        # Depo sistemi - Tohum deposu
        self.seed_stock = 999  # Sınırsız tohum
        
        # Elma (tarla bölgesinde)
        self.apple_food = Food(FARM_END * 0.3, SCREEN_HEIGHT // 2 - 50, FoodType.APPLE)
        
        # Level sistemi
        self.level = 1
        self.level_score_threshold = 50  # 50 puana ulaşınca Level 2'ye geç
        
        self.score = 0
        self.combo = 0
        self.deaths = 0
        self.time_elapsed = 0
        self.spawn_timer = 0
        self.spawn_interval = 8  # İlk at 8 saniye sonra
        self.min_spawn_interval = 3
        
        self.game_over = False
        self.game_over_time = 0
        
        # 3 adet at spawn et başlangıçta
        self.spawn_horse()
        self.spawn_horse()
        self.spawn_horse()
    
    def spawn_horse(self):
        """Yeni at spawn et"""
        if len(self.horses) < 3:
            spawn_index = len([h for h in self.horses if h.is_alive()])
            self.horses.append(Horse(spawn_index, level=self.level))
    
    def update(self, dt):
        if self.game_over:
            self.game_over_time += dt
            return
        
        # Oyuncu güncelle
        keys = pygame.key.get_pressed()
        self.player.update(keys, dt)
        
        # Zamanı güncelle
        self.time_elapsed += dt
        
        # Bitkileri güncelle
        for crop in self.crops:
            crop.update(dt)
        
        # Atları güncelle
        for horse in self.horses:
            horse.update(dt)
            if horse.state == HorseState.DEAD:
                # Bir at öldüyse oyun anında biter (mevcut dalga başarısız)
                self.deaths += 1
                self.game_over = True
                return
        
        # Spawn timer
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_horse()
            self.spawn_timer = 0
            # Spawn aralığını azalt (zorluk artar)
            self.spawn_interval = max(self.min_spawn_interval, self.spawn_interval - 0.3)
        
        # Oyuncu - Bitki etkileşimi (hasat etme)
        crops_to_remove = []
        for i, crop in enumerate(self.crops):
            if crop.state == CropState.MATURE:
                dist = ((self.player.x - crop.x)**2 + (self.player.y - crop.y)**2) ** 0.5
                if dist < 30:
                    # Oyuncu hasat etti
                    if self.player.harvest_carrot():
                        crops_to_remove.append(i)
        
        # Hasat edilen bitkileri kaldır (ters sırada)
        for i in reversed(crops_to_remove):
            self.crops.pop(i)
        
        # Oyuncu - Depo bölgesi etkileşimi (depodan tohum al)
        # Depo bölgesine girdiği an otomatik 5 tohum alır (ama sadece eli boş ise)
        storage_x = SCREEN_WIDTH // 2 - 150  # 430
        # Depo bölgesi dar ve spesifik: X ±75, Y ±20
        # X: 355-505 (tarla dışı), Y: 30-70 (üst alan)
        if (abs(self.player.x - storage_x) < 75 and abs(self.player.y - 50) < 20):
            # Depo bölgesine giriş yaptı (sadece EMPTY state'te tohum al)
            if self.player.state == PlayerState.EMPTY:
                self.player.seed_count = 5  # Direkt 5 tohum al
                self.player.state = PlayerState.CARRYING_SEED
                self.player.carrying_item = "SEED"
        
        # Tuş basış durumunu kontrol et (sadece yeni basış tespiti)
        e_pressed = keys[pygame.K_e]
        e_just_pressed = e_pressed and not self.prev_e_pressed
        self.prev_e_pressed = e_pressed
        
        # Oyuncu - Tarla etkileşimi (ekim yapma)
        # E tuşu ile tohum ek (sadece tuş basıldığında bir kez)
        if e_just_pressed:
            if self.player.x < FARM_END and self.player.state == PlayerState.CARRYING_SEED:
                # Tohum ekti
                new_crop = Crop(self.player.x, self.player.y)
                self.crops.append(new_crop)
                self.player.seed_count -= 1
                if self.player.seed_count == 0:
                    self.player.state = PlayerState.EMPTY
                    self.player.carrying_item = None
            # Oyuncu - Elma etkileşimi (E tuşu ile)
            # Elma yakınında olunca E tuşu ile al
            elif self.player.x < FARM_END:
                dist_to_apple = ((self.player.x - self.apple_food.x)**2 + 
                                (self.player.y - self.apple_food.y)**2) ** 0.5
                if dist_to_apple < 40:
                    self.player.pick_apple()
        
        # Oyuncu - At etkileşimi
        for horse in self.horses:
            if horse.is_alive():
                result = self.player.feed_horse(horse)
                # Skor sadece başarıyla beslemede artacak
                if result:
                    self.score += 10
                    self.combo += 1
                    if self.combo > 1:
                        self.score += self.combo * 2  # Bonus combo
        
        # Level kontrolü - 50 puana ulaşınca Level 2'ye geç
        if self.score >= self.level_score_threshold and self.level == 1:
            self.level = 2
            self.level_score_threshold = 150  # Sonraki level için daha yüksek puan
    
    def draw(self):
        # Arka plan çiz
        self.screen.fill(COLOR_GRASS)
        
        # ===== BÖLGE 1: TARLA (SOL TARAF) =====
        pygame.draw.rect(self.screen, (139, 90, 43), (0, 0, FARM_END, SCREEN_HEIGHT))
        
        # Tarla çizgileri (görsel)
        for i in range(0, SCREEN_HEIGHT, 30):
            pygame.draw.line(self.screen, (100, 60, 0), (0, i), (FARM_END, i), 1)
        for i in range(0, FARM_END, 30):
            pygame.draw.line(self.screen, (100, 60, 0), (i, 0), (i, SCREEN_HEIGHT), 1)
        
        # Tarla başlığı
        tarla_text = self.font_small.render("TARLA", True, COLOR_WHITE)
        self.screen.blit(tarla_text, (20, 10))
        
        # Level göstergesi
        level_text = self.font_small.render(f"Level: {self.level}", True, COLOR_YELLOW)
        self.screen.blit(level_text, (20, 40))
        
        # Ekili bitkileri çiz
        for crop in self.crops:
            crop.draw(self.screen, self.sprites)
        
        # ===== BÖLGE 2: OYUNCU (ORTA) =====
        # Açık yeşil arka plan (grass bölgesi)
        light_green = (180, 220, 100)
        pygame.draw.rect(self.screen, light_green, (FARM_END, 0, HORSES_START - FARM_END - 100, SCREEN_HEIGHT))
        
        # ===== DEPO VE SKOR TABLOSU - ÜSTTE YAN YANA =====
        # Depo sol taraf (daha gösterişli)
        storage_size = 110
        storage_x = SCREEN_WIDTH // 2 - 170
        storage_y = 60
        
        # Gölge efekti
        shadow_offset = 3
        pygame.draw.rect(self.screen, (0, 0, 0, 100), (storage_x - storage_size // 2 + shadow_offset, 
                                                        storage_y - storage_size // 2 + shadow_offset, 
                                                        storage_size, storage_size), border_radius=8)
        
        # Depo çerçevesi (kalın kare - kahverengi)
        storage_color = (180, 130, 70)  # Kahverengi
        pygame.draw.rect(self.screen, storage_color, (storage_x - storage_size // 2, 
                                                       storage_y - storage_size // 2, 
                                                       storage_size, storage_size), border_radius=8)
        pygame.draw.rect(self.screen, COLOR_BLACK, (storage_x - storage_size // 2, 
                                                     storage_y - storage_size // 2, 
                                                     storage_size, storage_size), 3, border_radius=8)
        
        # Depo yazısı
        depo_label = self.font_small.render("havuç tohumu", True, COLOR_WHITE)
        depo_label_rect = depo_label.get_rect(center=(storage_x, storage_y))
        self.screen.blit(depo_label, depo_label_rect)
        
        # Skor Tablosu - sağ taraf (YAN YANA tasarım)
        box_width = 95
        box_height = 95
        score_base_x = SCREEN_WIDTH // 2 + 160
        score_base_y = 70
        
        # SKOR KUTUSU (SOL)
        score_x = score_base_x - 60
        score_y = score_base_y
        
        # Gölge efekti
        shadow_offset = 2
        pygame.draw.rect(self.screen, (0, 0, 0, 100), (score_x - box_width // 2 + shadow_offset, 
                                                        score_y - box_height // 2 + shadow_offset, 
                                                        box_width, box_height), border_radius=8)
        
        # Kutu - Turuncu
        score_color = (255, 200, 0)
        pygame.draw.rect(self.screen, score_color, (score_x - box_width // 2, score_y - box_height // 2, 
                                                     box_width, box_height), border_radius=8)
        pygame.draw.rect(self.screen, COLOR_BLACK, (score_x - box_width // 2, score_y - box_height // 2, 
                                                     box_width, box_height), 3, border_radius=8)
        
        # Skor numarası (büyük)
        score_font = pygame.font.Font(None, 52)
        score_num = score_font.render(f"{self.score}", True, COLOR_BLACK)
        score_num_rect = score_num.get_rect(center=(score_x, score_y - 12))
        self.screen.blit(score_num, score_num_rect)
        
        # Skor etiketi
        score_label = self.font_small.render("SKOR", True, COLOR_BLACK)
        score_label_rect = score_label.get_rect(center=(score_x, score_y + 18))
        self.screen.blit(score_label, score_label_rect)
        
        # LEVEL KUTUSU (SAĞ)
        level_x = score_base_x + 60
        level_y = score_base_y
        
        # Gölge efekti
        pygame.draw.rect(self.screen, (0, 0, 0, 100), (level_x - box_width // 2 + shadow_offset, 
                                                        level_y - box_height // 2 + shadow_offset, 
                                                        box_width, box_height), border_radius=8)
        
        # Kutu - Mavi
        level_color = (100, 220, 255)
        pygame.draw.rect(self.screen, level_color, (level_x - box_width // 2, level_y - box_height // 2, 
                                                     box_width, box_height), border_radius=8)
        pygame.draw.rect(self.screen, COLOR_BLACK, (level_x - box_width // 2, level_y - box_height // 2, 
                                                     box_width, box_height), 3, border_radius=8)
        
        # Level numarası (büyük)
        level_num = score_font.render(f"{self.level}", True, COLOR_BLACK)
        level_num_rect = level_num.get_rect(center=(level_x, level_y - 12))
        self.screen.blit(level_num, level_num_rect)
        
        # Level etiketi
        level_label = self.font_small.render("LEVEL", True, COLOR_BLACK)
        level_label_rect = level_label.get_rect(center=(level_x, level_y + 18))
        self.screen.blit(level_label, level_label_rect)
        
        # ===== BÖLGE 3: ATLAR (SAĞ TARAF) =====
        # Açık yeşil arka plan
        light_green = (180, 220, 100)
        pygame.draw.rect(self.screen, light_green, (HORSES_START, 0, SCREEN_WIDTH - HORSES_START, SCREEN_HEIGHT))
        
        # Sınırlar çiz
        pygame.draw.line(self.screen, COLOR_BLACK, (FARM_END, 0), (FARM_END, SCREEN_HEIGHT), 3)
        
        # Atların beslenebileceği bölgeyi göstermek için sol tarafta dikey çizgi
        # Oyuncunun havuç verebileceği alan (atların solunda)
        horses_feed_boundary_x = HORSES_START - 100
        pygame.draw.line(self.screen, COLOR_BLACK, (horses_feed_boundary_x, 0), (horses_feed_boundary_x, SCREEN_HEIGHT), 3)
        
        # Atlar başlığı
        atlar_text = self.font_small.render("ATLAR", True, COLOR_BLACK)
        self.screen.blit(atlar_text, (HORSES_START + 30, 10))
        
        # Oyuncu çiz (sprite destekli)
        self.player.draw(self.screen, self.sprites)

        # Atlar çiz
        for horse in self.horses:
            horse.draw(self.screen, self.sprites)
        
        # ===== BILGI GÖSTERGESI (SAĞ ÜSTTE) =====
        # Zaman göstergesi (sol alt)
        time_text = self.font_small.render(f"Zaman: {int(self.time_elapsed)}s", True, COLOR_BLACK)
        self.screen.blit(time_text, (10, SCREEN_HEIGHT - 40))
        
        # ===== KONTROL TUŞLARI (SAĞ ALT KÖŞE) =====
        controls_x = SCREEN_WIDTH - 180
        controls_y = SCREEN_HEIGHT - 90
        
        # Kontrol kutusu
        pygame.draw.rect(self.screen, COLOR_WHITE, (controls_x - 10, controls_y - 10, 170, 80), border_radius=3)
        pygame.draw.rect(self.screen, COLOR_BLACK, (controls_x - 10, controls_y - 10, 170, 80), 1, border_radius=3)
        
        control_title = self.font_small.render("KONTROLLER", True, COLOR_BLACK)
        self.screen.blit(control_title, (controls_x, controls_y))
        
        control_lines = [
            "W/A/S/D - Hareket",
            "E - Ek/Depo/Hasat",
            "SPACE - Yeniden Başla"
        ]
        
        for i, line in enumerate(control_lines):
            control_text = pygame.font.Font(None, 16).render(line, True, COLOR_BLACK)
            self.screen.blit(control_text, (controls_x, controls_y + 22 + i * 16))
        
        # Game Over ekranı
        if self.game_over:
            # Yarı saydam overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(220)
            overlay.fill(COLOR_BLACK)
            self.screen.blit(overlay, (0, 0))
            
            # Game Over metni
            game_over_text = self.font_huge.render("GAME OVER", True, COLOR_RED)
            game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80))
            self.screen.blit(game_over_text, game_over_rect)
            
            final_score = self.font_large.render(f"Final Skor: {self.score}", True, COLOR_WHITE)
            score_rect = final_score.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
            self.screen.blit(final_score, score_rect)
            
            restart_text = self.font_small.render("Yeniden başlamak için SPACE'e basın", True, COLOR_WHITE)
            restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))
            self.screen.blit(restart_text, restart_rect)
        
        pygame.display.flip()
    
    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and self.game_over:
                    self.reset_game()
                elif event.key == pygame.K_ESCAPE:
                    return False
        
        return True
    
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0  # Delta time in seconds
            
            running = self.handle_input()
            self.update(dt)
            self.draw()
        
        pygame.quit()
        sys.exit()

# ============ BAŞLAT ============
if __name__ == "__main__":
    game = Game()
    game.run()
