"""
Replaced-style Fighting Game
A desktop fighting game with Freeflow combat system, round-based arena battles
with increasing number of opponents each round.
"""

import pygame
import math
import random
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Initialize Pygame
pygame.init()
try:
    pygame.mixer.init()
except:
    pass  # Audio not available in this environment

# Screen settings
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Colors (Replaced-inspired retro-futuristic palette)
COLOR_BG = (15, 15, 25)  # Dark blue-black
COLOR_RING = (30, 30, 45)  # Dark ring floor
COLOR_RING_BORDER = (200, 50, 50)  # Red neon border
COLOR_PLAYER = (50, 150, 250)  # Bright blue
COLOR_ENEMY = (250, 50, 50)  # Red
COLOR_HIT_EFFECT = (255, 200, 50)  # Yellow hit sparks
COLOR_COMBO_TEXT = (255, 100, 100)
COLOR_HEALTH_BAR_BG = (50, 50, 50)
COLOR_HEALTH_BAR_PLAYER = (50, 200, 50)
COLOR_HEALTH_BAR_ENEMY = (200, 50, 50)
COLOR_FREEFLOW_METER = (255, 150, 0)
COLOR_UI_TEXT = (200, 200, 220)
COLOR_ROUND_TEXT = (255, 200, 50)

# Combat constants
PLAYER_SPEED = 5
ENEMY_SPEED = 3
ATTACK_RANGE = 60
COMBO_WINDOW = 1.5  # seconds to continue combo
FREEFLOW_THRESHOLD = 3  # hits needed for freeflow mode
FREEFLOW_DAMAGE_MULTIPLIER = 1.5
MAX_COMBO = 20


class State(Enum):
    IDLE = "idle"
    MOVING = "moving"
    ATTACKING = "attacking"
    HIT = "hit"
    STUNNED = "stunned"
    BLOCKING = "blocking"
    DEAD = "dead"


class AttackType(Enum):
    LIGHT = "light"
    HEAVY = "heavy"
    SPECIAL = "special"


@dataclass
class HitEffect:
    x: float
    y: float
    timer: float = 0.3
    max_timer: float = 0.3
    size: int = 20


@dataclass
class FloatingText:
    text: str
    x: float
    y: float
    timer: float = 1.0
    color: Tuple[int, int, int] = COLOR_COMBO_TEXT
    velocity: float = -2


@dataclass
class Fighter:
    x: float
    y: float
    width: int = 40
    height: int = 70
    health: int = 100
    max_health: int = 100
    state: State = State.IDLE
    attack_timer: float = 0
    hit_stun_timer: float = 0
    combo_count: int = 0
    last_hit_time: float = 0
    is_player: bool = False
    damage: int = 10
    knockback_force: int = 10
    direction: int = 1  # 1 = right, -1 = left
    freeflow_active: bool = False
    freeflow_meter: int = 0
    invincible_timer: float = 0
    attack_type: Optional[AttackType] = None
    attack_frame: int = 0
    total_attack_frames: int = 15

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.x - self.width // 2,
            self.y - self.height // 2,
            self.width,
            self.height
        )

    def take_damage(self, damage: int, knockback_dir: int = 0):
        if self.state == State.DEAD or self.invincible_timer > 0:
            return
        
        self.health -= damage
        self.state = State.HIT
        self.hit_stun_timer = 0.5
        self.combo_count = 0
        
        if knockback_dir != 0:
            self.x += knockback_dir * self.knockback_force
        
        if self.health <= 0:
            self.health = 0
            self.state = State.DEAD

    def attack(self, target: 'Fighter', current_time: float) -> bool:
        if self.state in [State.HIT, State.STUNNED, State.DEAD]:
            return False
        
        if self.attack_timer > 0:
            return False
        
        # Check if target is in range
        dx = target.x - self.x
        dy = target.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance > ATTACK_RANGE:
            return False
        
        # Check facing direction
        if abs(dx) > 10 and (dx > 0) != (self.direction > 0):
            return False
        
        self.state = State.ATTACKING
        self.attack_timer = 0.3
        self.attack_frame = 0
        self.total_attack_frames = 15
        
        # Determine attack type based on combo
        if self.freeflow_active:
            self.attack_type = AttackType.SPECIAL
            actual_damage = int(self.damage * FREEFLOW_DAMAGE_MULTIPLIER)
        elif self.combo_count >= 5:
            self.attack_type = AttackType.HEAVY
            actual_damage = int(self.damage * 1.3)
        else:
            self.attack_type = AttackType.LIGHT
            actual_damage = self.damage
        
        # Deal damage after delay
        hit_frame = 5
        pygame.time.set_timer(pygame.USEREVENT + 1, int(1000 / FPS * hit_frame), loops=1)
        
        return True

    def update(self, dt: float, all_fighters: List['Fighter']):
        # Update timers
        if self.attack_timer > 0:
            self.attack_timer -= dt
            self.attack_frame += int(dt * FPS)
            if self.attack_frame >= self.total_attack_frames:
                self.state = State.IDLE
                self.attack_frame = 0
        
        if self.hit_stun_timer > 0:
            self.hit_stun_timer -= dt
            if self.hit_stun_timer <= 0:
                self.state = State.IDLE
        
        if self.invincible_timer > 0:
            self.invincible_timer -= dt
        
        # Update combo timer
        if self.combo_count > 0:
            if current_time_global - self.last_hit_time > COMBO_WINDOW:
                self.combo_count = 0
        
        # Update freeflow meter
        if self.is_player:
            if self.combo_count >= FREEFLOW_THRESHOLD:
                self.freeflow_active = True
                self.freeflow_meter = min(self.freeflow_meter + 1, 10)
            else:
                self.freeflow_active = False
                if self.freeflow_meter > 0:
                    self.freeflow_meter -= 0.1


current_time_global = 0


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Replaced Arena - Freeflow Combat")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 32)
        
        self.reset_game()
    
    def reset_game(self):
        self.round = 1
        self.enemies_per_round = 2
        self.player = Fighter(
            x=SCREEN_WIDTH // 2,
            y=SCREEN_HEIGHT // 2 + 100,
            is_player=True,
            damage=12
        )
        self.enemies: List[Fighter] = []
        self.hit_effects: List[HitEffect] = []
        self.floating_texts: List[FloatingText] = []
        self.game_over = False
        self.victory = False
        self.paused = False
        self.spawn_enemies()
    
    def spawn_enemies(self):
        self.enemies = []
        spawn_positions = [
            (SCREEN_WIDTH // 4, SCREEN_HEIGHT // 3),
            (3 * SCREEN_WIDTH // 4, SCREEN_HEIGHT // 3),
            (SCREEN_WIDTH // 4, 2 * SCREEN_HEIGHT // 3),
            (3 * SCREEN_WIDTH // 4, 2 * SCREEN_HEIGHT // 3),
            (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4),
            (SCREEN_WIDTH // 2, 3 * SCREEN_HEIGHT // 4),
        ]
        
        for i in range(min(self.enemies_per_round, len(spawn_positions))):
            pos = spawn_positions[i]
            enemy = Fighter(
                x=pos[0],
                y=pos[1],
                is_player=False,
                damage=8
            )
            enemy.direction = -1 if pos[0] > SCREEN_WIDTH // 2 else 1
            self.enemies.append(enemy)
    
    def handle_input(self):
        keys = pygame.key.get_pressed()
        
        if self.player.state not in [State.HIT, State.STUNNED, State.DEAD]:
            # Movement
            move_x = 0
            move_y = 0
            
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                move_y = -1
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                move_y = 1
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                move_x = -1
                self.player.direction = -1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                move_x = 1
                self.player.direction = 1
            
            if move_x != 0 or move_y != 0:
                self.player.state = State.MOVING
                # Normalize diagonal movement
                length = math.sqrt(move_x * move_x + move_y * move_y)
                move_x /= length
                move_y /= length
                
                new_x = self.player.x + move_x * PLAYER_SPEED
                new_y = self.player.y + move_y * PLAYER_SPEED
                
                # Keep player in ring
                ring_padding = 100
                new_x = max(ring_padding, min(SCREEN_WIDTH - ring_padding, new_x))
                new_y = max(ring_padding, min(SCREEN_HEIGHT - ring_padding, new_y))
                
                self.player.x = new_x
                self.player.y = new_y
            else:
                if self.player.state == State.MOVING:
                    self.player.state = State.IDLE
            
            # Attacks
            mouse_buttons = pygame.mouse.get_pressed()
            
            if mouse_buttons[0]:  # Left click - Light attack
                self.perform_attack(AttackType.LIGHT)
            elif mouse_buttons[2]:  # Right click - Heavy attack
                self.perform_attack(AttackType.HEAVY)
        
        # Block
        if keys[pygame.K_SPACE] and not self.player.state in [State.HIT, State.STUNNED, State.DEAD]:
            self.player.state = State.BLOCKING
        elif self.player.state == State.BLOCKING and not keys[pygame.K_SPACE]:
            self.player.state = State.IDLE
    
    def perform_attack(self, attack_type: AttackType):
        if self.player.state in [State.ATTACKING, State.HIT, State.STUNNED, State.DEAD]:
            return
        
        self.player.state = State.ATTACKING
        self.player.attack_timer = 0.4
        self.player.attack_frame = 0
        self.player.attack_type = attack_type
        
        # Set damage based on attack type
        if attack_type == AttackType.HEAVY:
            base_damage = int(self.player.damage * 1.5)
            knockback = 20
        else:
            base_damage = self.player.damage
            knockback = 10
        
        if self.player.freeflow_active:
            base_damage = int(base_damage * FREEFLOW_DAMAGE_MULTIPLIER)
        
        # Check collisions with enemies
        for enemy in self.enemies:
            if enemy.state == State.DEAD:
                continue
            
            dx = enemy.x - self.player.x
            dy = enemy.y - self.player.y
            distance = math.sqrt(dx * dx + dy * dy)
            
            # Check if in range and facing direction
            if distance <= ATTACK_RANGE:
                if abs(dx) < 10 or (dx > 0) == (self.player.direction > 0):
                    # Hit!
                    enemy.take_damage(base_damage, self.player.direction)
                    
                    # Add hit effect
                    self.hit_effects.append(HitEffect(
                        x=enemy.x,
                        y=enemy.y - enemy.height // 3,
                        size=30 if attack_type == AttackType.HEAVY else 20
                    ))
                    
                    # Update combo
                    global current_time_global
                    self.player.combo_count += 1
                    self.player.last_hit_time = current_time_global
                    
                    # Add floating text
                    self.floating_texts.append(FloatingText(
                        text=f"{base_damage}!",
                        x=enemy.x,
                        y=enemy.y - enemy.height,
                        color=COLOR_HIT_EFFECT if attack_type == AttackType.HEAVY else COLOR_COMBO_TEXT
                    ))
                    
                    if self.player.combo_count > 1:
                        self.floating_texts.append(FloatingText(
                            text=f"{self.player.combo_count}x COMBO!",
                            x=self.player.x,
                            y=self.player.y - 80,
                            color=COLOR_FREEFLOW_METER,
                            velocity=-3
                        ))
                    
                    if self.player.freeflow_active:
                        self.floating_texts.append(FloatingText(
                            text="FREEFLOW!",
                            x=self.player.x,
                            y=self.player.y - 100,
                            color=(255, 100, 200),
                            velocity=-4
                        ))
                    
                    break  # Only hit one enemy per attack
    
    def update_enemies_ai(self, dt: float):
        for enemy in self.enemies:
            if enemy.state == State.DEAD:
                continue
            
            if enemy.state in [State.HIT, State.STUNNED]:
                enemy.update(dt, [])
                continue
            
            # Simple AI: Move towards player and attack
            dx = self.player.x - enemy.x
            dy = self.player.y - enemy.y
            distance = math.sqrt(dx * dx + dy * dy)
            
            # Set direction
            if abs(dx) > 10:
                enemy.direction = 1 if dx > 0 else -1
            
            if distance > ATTACK_RANGE:
                # Move towards player
                enemy.state = State.MOVING
                move_x = dx / distance * ENEMY_SPEED
                move_y = dy / distance * ENEMY_SPEED
                
                new_x = enemy.x + move_x
                new_y = enemy.y + move_y
                
                # Keep in ring
                ring_padding = 100
                new_x = max(ring_padding, min(SCREEN_WIDTH - ring_padding, new_x))
                new_y = max(ring_padding, min(SCREEN_HEIGHT - ring_padding, new_y))
                
                enemy.x = new_x
                enemy.y = new_y
            else:
                # Attack player
                if random.random() < 0.02:  # 2% chance per frame to attack
                    if enemy.attack(enemy, current_time_global):
                        # Player takes damage
                        if self.player.state == State.BLOCKING:
                            blocked_damage = enemy.damage // 3
                            self.player.take_damage(blocked_damage, enemy.direction)
                            self.floating_texts.append(FloatingText(
                                text="BLOCKED!",
                                x=self.player.x,
                                y=self.player.y - 80,
                                color=(100, 100, 255)
                            ))
                        else:
                            self.player.take_damage(enemy.damage, enemy.direction)
                            self.hit_effects.append(HitEffect(
                                x=self.player.x,
                                y=self.player.y - self.player.height // 3,
                                size=25
                            ))
                            self.floating_texts.append(FloatingText(
                                text=f"-{enemy.damage}",
                                x=self.player.x,
                                y=self.player.y - self.player.height,
                                color=COLOR_ENEMY
                            ))
            
            enemy.update(dt, [])
    
    def check_round_status(self):
        # Check if all enemies are dead
        alive_enemies = [e for e in self.enemies if e.state != State.DEAD]
        
        if len(alive_enemies) == 0:
            # Round complete
            self.round += 1
            self.enemies_per_round += 1
            self.player.combo_count = 0
            self.player.freeflow_meter = 0
            self.player.freeflow_active = False
            
            # Heal player slightly
            self.player.health = min(self.player.max_health, self.player.health + 20)
            
            if self.enemies_per_round > 10:
                # Victory condition
                self.victory = True
                self.game_over = True
            else:
                self.spawn_enemies()
                self.floating_texts.append(FloatingText(
                    text=f"ROUND {self.round}!",
                    x=SCREEN_WIDTH // 2,
                    y=SCREEN_HEIGHT // 2,
                    color=COLOR_ROUND_TEXT,
                    velocity=0
                ))
        
        # Check if player is dead
        if self.player.state == State.DEAD:
            self.game_over = True
    
    def draw_ring(self):
        # Draw ring floor
        ring_rect = pygame.Rect(100, 100, SCREEN_WIDTH - 200, SCREEN_HEIGHT - 200)
        pygame.draw.rect(self.screen, COLOR_RING, ring_rect)
        
        # Draw grid pattern
        grid_size = 50
        for x in range(100, SCREEN_WIDTH - 100, grid_size):
            pygame.draw.line(self.screen, (40, 40, 60), (x, 100), (x, SCREEN_HEIGHT - 100), 2)
        for y in range(100, SCREEN_HEIGHT - 100, grid_size):
            pygame.draw.line(self.screen, (40, 40, 60), (100, y), (SCREEN_WIDTH - 100, y), 2)
        
        # Draw neon border
        pygame.draw.rect(self.screen, COLOR_RING_BORDER, ring_rect, 3)
        
        # Corner decorations
        corners = [
            (100, 100),
            (SCREEN_WIDTH - 100, 100),
            (100, SCREEN_HEIGHT - 100),
            (SCREEN_WIDTH - 100, SCREEN_HEIGHT - 100)
        ]
        for cx, cy in corners:
            pygame.draw.circle(self.screen, COLOR_RING_BORDER, (cx, cy), 15)
    
    def draw_fighter(self, fighter: Fighter):
        if fighter.state == State.DEAD:
            # Draw defeated fighter
            color = COLOR_PLAYER if fighter.is_player else COLOR_ENEMY
            pygame.draw.ellipse(self.screen, color, 
                              (fighter.x - 30, fighter.y - 10, 60, 20))
            return
        
        # Body glow effect
        glow_color = (*COLOR_PLAYER[:3], 100) if fighter.is_player else (*COLOR_ENEMY[:3], 100)
        if fighter.freeflow_active:
            glow_color = (255, 150, 0, 150)
        
        # Draw body
        color = COLOR_PLAYER if fighter.is_player else COLOR_ENEMY
        
        if fighter.state == State.ATTACKING:
            # Attack pose - extend arm
            arm_extension = fighter.attack_frame * 2
            pygame.draw.rect(self.screen, color,
                           (fighter.x - fighter.width // 2,
                            fighter.y - fighter.height // 2,
                            fighter.width, fighter.height))
            
            # Attack effect
            attack_end_x = fighter.x + fighter.direction * (30 + arm_extension)
            pygame.draw.circle(self.screen, COLOR_HIT_EFFECT,
                             (int(attack_end_x), fighter.y - 10), 15)
        else:
            # Normal stance
            pygame.draw.rect(self.screen, color,
                           (fighter.x - fighter.width // 2,
                            fighter.y - fighter.height // 2,
                            fighter.width, fighter.height))
        
        # Direction indicator (eyes)
        eye_offset = fighter.direction * 8
        pygame.draw.circle(self.screen, (255, 255, 255),
                         (int(fighter.x + eye_offset), int(fighter.y - 20)), 6)
        
        # Health bar above head
        bar_width = 60
        bar_height = 6
        bar_x = fighter.x - bar_width // 2
        bar_y = fighter.y - fighter.height // 2 - 15
        
        pygame.draw.rect(self.screen, COLOR_HEALTH_BAR_BG,
                        (bar_x, bar_y, bar_width, bar_height))
        
        health_ratio = fighter.health / fighter.max_health
        bar_color = COLOR_HEALTH_BAR_PLAYER if fighter.is_player else COLOR_HEALTH_BAR_ENEMY
        pygame.draw.rect(self.screen, bar_color,
                        (bar_x, bar_y, int(bar_width * health_ratio), bar_height))
    
    def draw_hit_effects(self):
        for effect in self.hit_effects:
            effect.timer -= 1 / FPS
            if effect.timer <= 0:
                continue
            
            alpha = int(255 * (effect.timer / effect.max_timer))
            size = int(effect.size * (effect.timer / effect.max_timer))
            
            # Draw spark effect
            for i in range(8):
                angle = (i / 8) * math.pi * 2
                spark_x = effect.x + math.cos(angle) * size * 0.5
                spark_y = effect.y + math.sin(angle) * size * 0.5
                pygame.draw.circle(self.screen, COLOR_HIT_EFFECT,
                                 (int(spark_x), int(spark_y)), 3)
    
    def draw_floating_texts(self):
        for text_obj in self.floating_texts:
            text_obj.timer -= 1 / FPS
            text_obj.y += text_obj.velocity
            
            if text_obj.timer <= 0:
                continue
            
            alpha = int(255 * (text_obj.timer / 1.0))
            text_surface = self.font_small.render(text_obj.text, True, text_obj.color)
            text_rect = text_surface.get_rect(center=(int(text_obj.x), int(text_obj.y)))
            self.screen.blit(text_surface, text_rect)
    
    def draw_ui(self):
        # Player health bar
        bar_width = 300
        bar_height = 20
        bar_x = 20
        bar_y = 20
        
        pygame.draw.rect(self.screen, COLOR_HEALTH_BAR_BG,
                        (bar_x, bar_y, bar_width, bar_height))
        
        health_ratio = self.player.health / self.player.max_health
        pygame.draw.rect(self.screen, COLOR_HEALTH_BAR_PLAYER,
                        (bar_x, bar_y, int(bar_width * health_ratio), bar_height))
        
        pygame.draw.rect(self.screen, COLOR_UI_TEXT,
                        (bar_x, bar_y, bar_width, bar_height), 2)
        
        # Player label
        label = self.font_small.render("PLAYER", True, COLOR_UI_TEXT)
        self.screen.blit(label, (bar_x, bar_y - 25))
        
        # Combo counter
        if self.player.combo_count > 1:
            combo_text = self.font_medium.render(f"x{self.player.combo_count} COMBO", True, COLOR_COMBO_TEXT)
            combo_rect = combo_text.get_rect(center=(SCREEN_WIDTH // 2, 60))
            self.screen.blit(combo_text, combo_rect)
        
        # Freeflow meter
        meter_width = 200
        meter_height = 15
        meter_x = SCREEN_WIDTH - meter_width - 20
        meter_y = 20
        
        pygame.draw.rect(self.screen, COLOR_HEALTH_BAR_BG,
                        (meter_x, meter_y, meter_width, meter_height))
        
        if self.player.freeflow_active:
            meter_color = COLOR_FREEFLOW_METER
        else:
            meter_fill = min(self.player.freeflow_meter / 10, 1.0)
            meter_color = (int(255 * meter_fill), int(150 * meter_fill), 0)
        
        meter_fill = min(self.player.freeflow_meter / 10, 1.0)
        pygame.draw.rect(self.screen, meter_color,
                        (meter_x, meter_y, int(meter_width * meter_fill), meter_height))
        
        ff_label = self.font_small.render("FREEFLOW", True, COLOR_UI_TEXT)
        self.screen.blit(ff_label, (meter_x, meter_y - 25))
        
        # Round counter
        round_text = self.font_medium.render(f"ROUND {self.round}", True, COLOR_ROUND_TEXT)
        round_rect = round_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30))
        self.screen.blit(round_text, round_rect)
        
        # Enemies remaining
        enemies_alive = len([e for e in self.enemies if e.state != State.DEAD])
        enemy_text = self.font_small.render(f"ENEMIES: {enemies_alive}", True, COLOR_ENEMY)
        self.screen.blit(enemy_text, (20, SCREEN_HEIGHT - 40))
        
        # Controls hint
        controls = self.font_small.render("WASD: Move | LMB: Light Attack | RMB: Heavy Attack | SPACE: Block",
                                         True, (100, 100, 100))
        controls_rect = controls.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 10))
        self.screen.blit(controls, controls_rect)
    
    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(180)
        self.screen.blit(overlay, (0, 0))
        
        if self.victory:
            text = self.font_large.render("VICTORY!", True, COLOR_HEALTH_BAR_PLAYER)
        else:
            text = self.font_large.render("GAME OVER", True, COLOR_ENEMY)
        
        text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        self.screen.blit(text, text_rect)
        
        subtext = self.font_medium.render(f"Reached Round {self.round}", True, COLOR_UI_TEXT)
        subtext_rect = subtext.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        self.screen.blit(subtext, subtext_rect)
        
        restart_text = self.font_small.render("Press R to Restart", True, COLOR_UI_TEXT)
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80))
        self.screen.blit(restart_text, restart_rect)
    
    def run(self):
        running = True
        global current_time_global
        
        while running:
            current_time_global = pygame.time.get_ticks() / 1000.0
            
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r and self.game_over:
                        self.reset_game()
                    if event.key == pygame.K_ESCAPE:
                        running = False
            
            if not self.paused and not self.game_over:
                self.handle_input()
                self.player.update(1 / FPS, self.enemies)
                self.update_enemies_ai(1 / FPS)
                self.check_round_status()
            
            # Clean up old effects
            self.hit_effects = [e for e in self.hit_effects if e.timer > 0]
            self.floating_texts = [t for t in self.floating_texts if t.timer > 0]
            
            # Drawing
            self.screen.fill(COLOR_BG)
            self.draw_ring()
            
            # Draw fighters
            for enemy in self.enemies:
                self.draw_fighter(enemy)
            self.draw_fighter(self.player)
            
            # Draw effects
            self.draw_hit_effects()
            self.draw_floating_texts()
            
            # Draw UI
            self.draw_ui()
            
            if self.game_over:
                self.draw_game_over()
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        pygame.quit()


if __name__ == "__main__":
    game = Game()
    game.run()
