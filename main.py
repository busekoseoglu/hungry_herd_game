import pygame
import sys
import os
import random
import math
import asyncio
from typing import List, Optional

import constants
from enums import FoodType, HorseState, PlayerState, CropState
from entities import Player, Horse, Crop, AppleTree, Poop
from assets_loader import AssetsLoader

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
        pygame.display.set_caption("Feed the Herd")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_large = pygame.font.SysFont("Arial", 40, bold=True)
        self.version = "v1.0.9"
        
        # Assets
        self.loader = AssetsLoader(os.path.join(os.getcwd(), "assets"))
        self.sprites = self.loader.load_all()
        
        # Entities
        self.player = Player()
        self.horses: List[Horse] = []
        self.crops: List[Crop] = []
        self.apple_trees: List[AppleTree] = []
        self.poops: List[Poop] = []
        
        # Level system
        self.level = 1
        self.score = 0
        self.level_up_timer = 0.0 # Message display timer
        
        # Shop
        self.shop_open = False
        
        self._spawn_initial_horses()

    def _spawn_initial_horses(self):
        # Center horses vertically in the right column
        right_center_x = constants.HORSES_START + (constants.SCREEN_WIDTH - constants.HORSES_START) // 2
        self.horses = []
        for i in range(3):
            h = Horse(i, self.level, can_have_three=(i == 0))
            h.x = right_center_x
            h.y = 180 + i * 200 # Balanced vertical spacing
            self.horses.append(h)

    def _draw_text(self, text, pos, color, font):
        surf = font.render(text, True, color)
        self.screen.blit(surf, pos)

    def _draw_centered_text(self, text, y, color, font):
        surf = font.render(text, True, color)
        rect = surf.get_rect(center=(constants.SCREEN_WIDTH//2, y))
        self.screen.blit(surf, rect)

    async def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            self._handle_events()
            if not self.shop_open:
                self._update(dt)
            self._draw()
            await asyncio.sleep(0)

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # Toggle Shop or Trash
                    if abs(self.player.x - constants.STORAGE_X) < 120 and abs(self.player.y - constants.STORAGE_Y) < 120:
                        self.shop_open = not self.shop_open
                    elif abs(self.player.x - constants.TRASH_X) < 120 and abs(self.player.y - constants.TRASH_Y) < 120:
                        self._handle_interaction()
                    else:
                        self.shop_open = False
                
                if event.key == pygame.K_e:
                    self._handle_interaction()

                # Shop keyboard shortcuts
                if self.shop_open:
                    if event.key == pygame.K_1 or event.key == pygame.K_KP1:
                        self._buy_item("CARROT_SEEDS")
                    if (event.key == pygame.K_2 or event.key == pygame.K_KP2) and self.level >= 2:
                        self._buy_item("APPLE_SAPLING")
                    if (event.key == pygame.K_3 or event.key == pygame.K_KP3) and self.score >= 100:
                        self._buy_item("SPEED_BOOTS")
                    if (event.key == pygame.K_4 or event.key == pygame.K_KP4) and self.score >= 100:
                        self._buy_item("BIG_BASKET")

    def _buy_item(self, item_type: str) -> bool:
        if item_type == "CARROT_SEEDS":
            cost = constants.CARROT_SEED_PRICE * 5
            if self.player.coins >= cost and self.player.carrot_seeds == 0:
                self.player.coins -= cost
                self.player.carrot_seeds = 5
                self.shop_open = False
                if "SEED" not in self.player.items:
                    self.player.items.append("SEED")
                return True
        elif item_type == "APPLE_SAPLING":
            cost = constants.APPLE_SAPLING_PRICE
            if self.player.coins >= cost and self.player.apple_saplings < 2:
                self.player.coins -= cost
                self.player.apple_saplings += 1
                self.shop_open = False
                if "SAPLING" not in self.player.items:
                    self.player.items.append("SAPLING")
                return True
        elif item_type == "SPEED_BOOTS":
            if self.score < 100: return False
            cost = constants.UPGRADE_SPEED_BOOST_PRICE
            if self.player.coins >= cost:
                self.player.coins -= cost
                self.player.speed_boost_timer += constants.UPGRADE_DURATION
                self.shop_open = False
                return True
        elif item_type == "BIG_BASKET":
            if self.score < 100: return False
            cost = constants.UPGRADE_BASKET_PRICE
            if self.player.coins >= cost:
                self.player.coins -= cost
                self.player.basket_timer += constants.UPGRADE_DURATION
                self.shop_open = False
                return True
        return False

    def _check_horse_finished(self, horse: Horse):
        if horse.is_finished():
            # Poop chance - Spawn BEHIND horse (further right: +100)
            # Poop logic: Level 1: Guaranteed every 2nd feeding. Level 2+: Guaranteed every feeding.
            should_spawn = (self.level >= 2) or (horse.feedings_count % 2 == 0)
            if should_spawn:
                self.poops.append(Poop(horse.x + 100, horse.y + 10))
            
            # Reset horse: only one horse can have 3 items at a time
            triples = sum(1 for h in self.horses if len(h.wanted_items) == 3 and h != horse)
            horse.reset(self.level, (triples == 0))

    def _handle_interaction(self):
        if self.shop_open: return
        
        # Standing at Shop to pick up seeds manually (if needed)
        if abs(self.player.x - constants.STORAGE_X) < 100 and abs(self.player.y - constants.STORAGE_Y) < 100:
            max_cap = 3 if self.player.basket_timer > 0 else 1
            if len(self.player.items) < max_cap:
                if self.player.carrot_seeds > 0 and "SEED" not in self.player.items:
                    self.player.items.append("SEED")
                    return
                elif self.player.apple_saplings > 0 and "SAPLING" not in self.player.items:
                    self.player.items.append("SAPLING")
                    return
        
        # Trash interaction
        if abs(self.player.x - constants.TRASH_X) < 100 and abs(self.player.y - constants.TRASH_Y) < 100:
            if self.player.items:
                self.player.items.pop() # Trash last item
                return

        # 5. Plant (This remains manual with E)
        if self.player.x < constants.FARM_END:
            if "SEED" in self.player.items and self.player.y < constants.FARM_MID_Y:
                self.crops.append(Crop(self.player.x, self.player.y))
                self.player.carrot_seeds -= 1
                if self.player.carrot_seeds <= 0:
                    self.player.items.remove("SEED")
                return
            elif "SAPLING" in self.player.items and self.player.y >= constants.FARM_MID_Y:
                self.apple_trees.append(AppleTree(self.player.x, self.player.y))
                self.player.apple_saplings -= 1
                if self.player.apple_saplings <= 0:
                    self.player.items.remove("SAPLING")
                return


    def _update(self, dt):
        if self.level_up_timer > 0:
            self.level_up_timer -= dt
            
        # Global Level Up Check
        if self.score >= constants.LEVEL_UP_SCORE and self.level == 1:
            self.level = 2
            self.level_up_timer = 3.0
            for i, horse in enumerate(self.horses):
                horse.reset(self.level, can_have_three=(i == 0))

        self.player.move(pygame.key.get_pressed(), dt)
        for crop in self.crops: crop.update(dt)
        for tree in self.apple_trees: tree.update(dt)
        for horse in self.horses: horse.update(dt)
        
        # Automatic Interactions (Walking over/near)
        if not self.shop_open:
            self._handle_automatic_interactions()

    def _handle_automatic_interactions(self):
        # Determine max capacity
        max_items = 3 if self.player.basket_timer > 0 else 1

        # 1. Auto-Harvest Crops
        for crop in self.crops[:]:
            if len(self.player.items) >= max_items: break
            if crop.state == CropState.MATURE:
                dist = math.sqrt((self.player.x - crop.x)**2 + (self.player.y - crop.y)**2)
                if dist < 35:
                    self.crops.remove(crop)
                    self.player.items.append("CARROT")
        
        # 2. Auto-Harvest Trees
        for tree in self.apple_trees[:]:
            if len(self.player.items) >= max_items: break
            if tree.state == "READY" and tree.apples_left > 0:
                dist = math.sqrt((self.player.x - tree.x)**2 + (self.player.y - tree.y)**2)
                if dist < 50:
                    tree.harvest()
                    self.player.items.append("APPLE")
                    if tree.apples_left == 0:
                        self.apple_trees.remove(tree)
        
        # 3. Auto-Collect Poop
        for poop in self.poops[:]:
            if len(self.player.items) >= max_items: break
            dist = math.sqrt((self.player.x - poop.x)**2 + (self.player.y - poop.y)**2)
            if dist < 35:
                self.poops.remove(poop)
                self.player.items.append("POOP")
        
        # 4. Auto-Sell Poop
        if "POOP" in self.player.items:
            if abs(self.player.x - constants.STORAGE_X) < 80 and abs(self.player.y - constants.STORAGE_Y) < 80:
                self.player.coins += constants.POOP_VALUE
                self.player.items.remove("POOP")

        # 5. Auto-Feed Horses
        for horse in self.horses:
            dist = math.sqrt((self.player.x - horse.x)**2 + (self.player.y - horse.y)**2)
            if dist < 65 and horse.state == HorseState.WAITING:
                # Try to give items from inventory
                for item in self.player.items[:]:
                    f_type = FoodType.CARROT if item == "CARROT" else FoodType.APPLE if item == "APPLE" else None
                    if f_type and horse.receive_food(f_type):
                        self.score += 10
                        self.player.items.remove(item)
                        self._check_horse_finished(horse)
                        # Carry on to feed other items if possible!

    def _draw(self):
        # 1. Fill background (Grass)
        for x in range(0, constants.SCREEN_WIDTH, 100):
            for y in range(0, constants.SCREEN_HEIGHT, 100):
                self.screen.blit(self.sprites['bg_farm_bottom'], (x, y))
                
        # 2. Carrot Field
        carrot_field_surf = pygame.Surface((constants.FARM_END, constants.FARM_MID_Y), pygame.SRCALPHA)
        carrot_field_surf.blit(self.sprites['bg_farm_top'], (0, 0))
        mask = pygame.Surface((constants.FARM_END, constants.FARM_MID_Y), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, constants.FARM_END, constants.FARM_MID_Y), 
                         border_top_right_radius=50, border_bottom_right_radius=50)
        carrot_field_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.screen.blit(carrot_field_surf, (0, 0))
        
        # 3. Shop
        self._draw_text("ATLAR", (constants.HORSES_START + 10, 20), constants.COLOR_BLACK, self.font_small)
        shop_spr = self.sprites.get('shop_stall')
        if shop_spr:
            self.screen.blit(shop_spr, (constants.STORAGE_X - 80, constants.STORAGE_Y - 80))
            
        trash_spr = self.sprites.get('trash')
        if trash_spr:
            self.screen.blit(trash_spr, (constants.TRASH_X - 40, constants.TRASH_Y - 40))
            
        # Draw Prompts (Dynamic based on proximity)
        if abs(self.player.x - constants.TRASH_X) < 100 and abs(self.player.y - constants.TRASH_Y) < 100:
            if self.player.items:
                # Position it above the trash bin
                text_x = constants.TRASH_X - 40
                text_y = constants.TRASH_Y - 100
                self._draw_text("[SPACE] Çöpe At", (text_x, text_y), constants.COLOR_WHITE, self.font_small)
        
        # 4. Entities
        for crop in self.crops: crop.draw(self.screen, self.sprites)
        for tree in self.apple_trees: tree.draw(self.screen, self.sprites)
        for poop in self.poops: poop.draw(self.screen, self.sprites)
        for horse in self.horses: horse.draw(self.screen, self.sprites)
        self.player.draw(self.screen, self.sprites)
        
        # 5. UI (Compact Top Center)
        ui_y = constants.UI_BASE_Y
        self._draw_stat_box(constants.SCREEN_WIDTH // 2 - 110, ui_y, str(self.score), "SKOR", (255, 200, 50))
        self._draw_stat_box(constants.SCREEN_WIDTH // 2, ui_y, str(self.level), "LEVEL", (80, 200, 255))
        self._draw_stat_box(constants.SCREEN_WIDTH // 2 + 110, ui_y, str(self.player.coins), "PARA", (255, 255, 100))
        
        # Bottom UI (inventory)
        seed_text = f"TOHUM: {self.player.carrot_seeds}"
        self._draw_text(seed_text, (20, constants.SCREEN_HEIGHT - 40), constants.COLOR_BLACK, self.font_small)

        if self.level >= 2:
            sap_text = f"FİDAN: {self.player.apple_saplings}"
            self._draw_text(sap_text, (150, constants.SCREEN_HEIGHT - 40), constants.COLOR_BLACK, self.font_small)

        if self.level_up_timer > 0:
            msg = f"LEVEL {self.level}!"
            surf = self.font_large.render(msg, True, (255, 100, 0))
            rect = surf.get_rect(center=(constants.SCREEN_WIDTH//2, constants.SCREEN_HEIGHT//2))
            # Shadow
            self.screen.blit(self.font_large.render(msg, True, (0,0,0)), rect.move(3,3))
            self.screen.blit(surf, rect)

        # 6. Active Power-ups (Timers) - Top Center below Level
        timer_y = 115
        if self.player.speed_boost_timer > 0:
            msg = f"HIZ: {int(self.player.speed_boost_timer)}s"
            self._draw_centered_text(msg, timer_y, (255, 100, 0), self.font_small)
            timer_y += 25
        if self.player.basket_timer > 0:
            msg = f"SEPET: {int(self.player.basket_timer)}s"
            self._draw_centered_text(msg, timer_y, (0, 255, 100), self.font_small)

        # Version tag
        self._draw_text(self.version, (constants.SCREEN_WIDTH - 60, constants.SCREEN_HEIGHT - 30), (100, 100, 100), self.font_small)

        if self.shop_open:
            self._draw_shop_popup()
            
        self._draw_interaction_prompts()
        
        pygame.display.flip()

    def _draw_stat_box(self, x, y, val, title, color):
        width, height = constants.BOX_WIDTH, constants.BOX_HEIGHT
        rect = pygame.Rect(x - width//2, y - height//2, width, height)
        # Compact style
        pygame.draw.rect(self.screen, (0,0,0,30), rect.move(3,3), border_radius=12)
        pygame.draw.rect(self.screen, color, rect, border_radius=12)
        pygame.draw.rect(self.screen, (30,30,30), rect, width=2, border_radius=12)
        
        val_surf = self.font_large.render(val, True, constants.COLOR_BLACK)
        v_rect = val_surf.get_rect(center=(x, y-8))
        self.screen.blit(val_surf, v_rect)
        
        title_surf = self.font_small.render(title, True, constants.COLOR_BLACK)
        t_rect = title_surf.get_rect(center=(x, y + 18))
        self.screen.blit(title_surf, t_rect)

    def _draw_shop_popup(self):
        w, h = 500, 350
        overlay_x = (constants.SCREEN_WIDTH - w) // 2
        overlay_y = (constants.SCREEN_HEIGHT - h) // 2
        
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (0, 0, 0, 220), (0, 0, w, h), border_radius=25)
        self.screen.blit(overlay, (overlay_x, overlay_y))
        
        # Draw items relative to popup position
        self._draw_text("PAZAR - SHOP", (overlay_x + 100, overlay_y + 30), (255, 255, 255), self.font_large)
        self._draw_text(f"[1] Havuç Tohumu (5x) - {constants.CARROT_SEED_PRICE * 5}", (overlay_x + 50, overlay_y + 90), (255, 255, 255), self.font_small)
        if self.level >= 2:
            self._draw_text(f"[2] Elma Fidanı (1x) - {constants.APPLE_SAPLING_PRICE}", (overlay_x + 50, overlay_y + 130), (255, 255, 255), self.font_small)
        
        # Upgrades
        if self.score < 100:
            self._draw_text("[!] Upgradeler 100 Puanda Açılır", (overlay_x + 50, overlay_y + 180), (255, 100, 100), self.font_small)
        else:
            self._draw_text(f"[3] Hız Botu (15sn) - {constants.UPGRADE_SPEED_BOOST_PRICE}", (overlay_x + 50, overlay_y + 180), (255, 150, 50), self.font_small)
            self._draw_text(f"[4] Büyük Sepet (15sn) - {constants.UPGRADE_BASKET_PRICE}", (overlay_x + 50, overlay_y + 220), (50, 255, 150), self.font_small)
        
        self._draw_text("[SPACE] Kapat", (overlay_x + 180, overlay_y + 310), (200, 200, 200), self.font_small)

    def _draw_interaction_prompts(self):
        # Interaction hints
        prompt = ""
        # Shop prompt
        if abs(self.player.x - constants.STORAGE_X) < 100 and abs(self.player.y - constants.STORAGE_Y) < 100:
            prompt = "[SPACE] Marketi Aç"
        
        # Plant hint
        if any(item in self.player.items for item in ["SEED", "SAPLING"]) and self.player.x < constants.FARM_END:
            prompt = "[E] Ek"

        if prompt:
            self._draw_centered_text(prompt, self.player.y - 70, constants.COLOR_BLACK, self.font_small)

if __name__ == "__main__":
    game = Game()
    asyncio.run(game.run())
