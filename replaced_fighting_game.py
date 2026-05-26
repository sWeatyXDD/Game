"""
Replaced-style Fighting Game with Freeflow Combat System
Enhanced version with procedural character sprites and animations
"""

import pygame
import math
import random
import sys
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Инициализация Pygame
pygame.init()
pygame.mixer.init()

# Константы экрана
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Цветовая палитра в стиле Replaced (ретро-футуризм)
COLORS = {
    'background_dark': (15, 15, 25),
    'background_mid': (25, 25, 40),
    'neon_blue': (0, 200, 255),
    'neon_pink': (255, 0, 150),
    'neon_green': (0, 255, 150),
    'neon_yellow': (255, 200, 0),
    'neon_red': (255, 50, 50),
    'player_skin': (200, 180, 160),
    'player_suit': (30, 40, 60),
    'enemy_skin': (180, 160, 140),
    'enemy_suit': (60, 30, 30),
    'ring_floor': (40, 40, 50),
    'ring_rope': (200, 50, 50),
    'ui_bg': (10, 10, 20, 180),
    'ui_text': (200, 220, 255),
    'freeflow_glow': (0, 255, 200),
    'hit_effect': (255, 255, 200),
}

class EntityState(Enum):
    IDLE = "idle"
    WALK = "walk"
    PUNCH = "punch"
    KICK = "kick"
    BLOCK = "block"
    HIT = "hit"
    KNOCKDOWN = "knockdown"
    VICTORY = "victory"

@dataclass
class AnimationFrame:
    """Кадр анимации с параметрами сегментов тела"""
    body_angle: float = 0.0
    head_offset: Tuple[float, float] = (0, 0)
    arm_l_angle: float = 0.0
    arm_r_angle: float = 0.0
    leg_l_angle: float = 0.0
    leg_r_angle: float = 0.0
    arm_l_extend: float = 0.0
    arm_r_extend: float = 0.0
    scale: float = 1.0

class Character:
    """Класс персонажа с процедурной анимацией"""
    
    def __init__(self, x: float, y: float, is_player: bool = True):
        self.x = x
        self.y = y
        self.is_player = is_player
        self.width = 50
        self.height = 120
        
        # Статистика
        self.health = 100
        self.max_health = 100
        self.speed = 5
        self.damage = 10
        self.block_damage_mult = 0.3
        
        # Состояние
        self.state = EntityState.IDLE
        self.facing_right = True if is_player else False
        self.combo_count = 0
        self.freeflow_active = False
        self.freeflow_timer = 0
        self.hit_stun = 0
        self.knockdown_timer = 0
        self.block_active = False
        self.attack_cooldown = 0
        self.invincible = 0
        
        # Анимация
        self.animation_frame = 0
        self.animation_speed = 0.15
        self.current_animation: List[AnimationFrame] = []
        
        # Физика
        self.velocity_y = 0
        self.on_ground = True
        self.gravity = 0.8
        
        # Настройка цветов
        self.skin_color = COLORS['player_skin'] if is_player else COLORS['enemy_skin']
        self.suit_color = COLORS['player_suit'] if is_player else COLORS['enemy_suit']
        self.glow_color = COLORS['neon_blue'] if is_player else COLORS['neon_red']
        
        # Загрузка анимаций
        self.animations = self._create_animations()
        
    def _create_animations(self) -> dict:
        """Создание всех анимаций"""
        animations = {}
        
        # Idle анимация
        idle_frames = []
        for i in range(8):
            angle = math.sin(i * 0.5) * 3
            idle_frames.append(AnimationFrame(
                body_angle=angle,
                head_offset=(math.sin(i * 0.3) * 2, math.cos(i * 0.3) * 2),
                arm_l_angle=-10 + math.sin(i * 0.5) * 5,
                arm_r_angle=10 + math.sin(i * 0.5 + 1) * 5,
                leg_l_angle=math.sin(i * 0.3) * 3,
                leg_r_angle=math.sin(i * 0.3 + 2) * 3
            ))
        animations['idle'] = idle_frames
        
        # Walk анимация
        walk_frames = []
        for i in range(8):
            walk_frames.append(AnimationFrame(
                body_angle=math.sin(i * 0.8) * 8,
                head_offset=(math.sin(i * 0.4) * 3, abs(math.cos(i * 0.8)) * 5),
                arm_l_angle=-30 + math.sin(i * 0.8) * 20,
                arm_r_angle=30 + math.sin(i * 0.8 + 3) * 20,
                leg_l_angle=45 * math.sin(i * 0.8),
                leg_r_angle=45 * math.sin(i * 0.8 + 3.14),
                scale=1 + abs(math.sin(i * 0.8)) * 0.05
            ))
        animations['walk'] = walk_frames
        
        # Punch анимация
        punch_frames = []
        for i in range(6):
            progress = i / 5
            if i < 3:
                extend = progress * 40
                body_rot = -20 * progress
            else:
                extend = 40 - (progress - 0.6) * 60
                body_rot = -20 + (progress - 0.6) * 30
            punch_frames.append(AnimationFrame(
                body_angle=body_rot,
                arm_r_angle=-90 + extend * 0.5,
                arm_r_extend=extend,
                leg_l_angle=-20,
                leg_r_angle=30
            ))
        animations['punch'] = punch_frames
        
        # Kick анимация
        kick_frames = []
        for i in range(8):
            progress = i / 7
            if i < 4:
                leg_ext = progress * 70
                body_rot = -15 * progress
            else:
                leg_ext = 70 - (progress - 0.5) * 80
                body_rot = -15 + (progress - 0.5) * 20
            kick_frames.append(AnimationFrame(
                body_angle=body_rot,
                leg_r_angle=-leg_ext,
                arm_l_angle=-45,
                arm_r_angle=45,
                scale=1.05
            ))
        animations['kick'] = kick_frames
        
        # Block анимация
        block_frames = []
        for i in range(4):
            block_frames.append(AnimationFrame(
                arm_l_angle=-120,
                arm_r_angle=-100,
                arm_l_extend=10,
                arm_r_extend=10,
                body_angle=-5
            ))
        animations['block'] = block_frames
        
        # Hit анимация
        hit_frames = []
        for i in range(4):
            hit_frames.append(AnimationFrame(
                body_angle=20 + i * 5,
                head_offset=(15, -10),
                arm_l_angle=60,
                arm_r_angle=80,
                scale=0.95
            ))
        animations['hit'] = hit_frames
        
        return animations
    
    def update(self, keys: dict, enemies: List['Character'], particles: List):
        """Обновление состояния персонажа"""
        
        # Обновление таймеров
        if self.hit_stun > 0:
            self.hit_stun -= 1
            self.state = EntityState.HIT
            return
            
        if self.knockdown_timer > 0:
            self.knockdown_timer -= 1
            self.state = EntityState.KNOCKDOWN
            return
            
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
            
        if self.invincible > 0:
            self.invincible -= 1
            
        # Freeflow таймер
        if self.freeflow_active:
            self.freeflow_timer -= 1
            if self.freeflow_timer <= 0:
                self.freeflow_active = False
                self.combo_count = 0
        
        # Гравитация
        if not self.on_ground:
            self.velocity_y += self.gravity
            self.y += self.velocity_y
            if self.y >= SCREEN_HEIGHT - 150:
                self.y = SCREEN_HEIGHT - 150
                self.velocity_y = 0
                self.on_ground = True
        
        # Управление игроком
        if self.is_player and self.hit_stun == 0:
            self._handle_player_input(keys, enemies, particles)
        elif not self.is_player:
            self._handle_ai(enemies[0] if enemies and enemies[0].is_player else None, particles)
        
        # Обновление анимации
        self._update_animation()
    
    def _handle_player_input(self, keys: dict, enemies: List['Character'], particles: List):
        """Обработка ввода игрока"""
        moving = False
        
        # Движение
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.x -= self.speed
            self.facing_right = False
            moving = True
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.x += self.speed
            self.facing_right = True
            moving = True
        
        # Прыжок
        if (keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE]) and self.on_ground:
            self.velocity_y = -15
            self.on_ground = False
        
        # Блок
        self.block_active = keys[pygame.K_s] or keys[pygame.K_DOWN]
        
        # Атаки
        if self.attack_cooldown == 0:
            if keys[pygame.K_j] or keys[pygame.BUTTON_LEFT]:
                self._perform_attack('punch', enemies, particles)
            elif keys[pygame.K_k] or keys[pygame.BUTTON_RIGHT]:
                self._perform_attack('kick', enemies, particles)
        
        # Установка состояния
        if self.block_active:
            self.state = EntityState.BLOCK
        elif moving:
            self.state = EntityState.WALK
        elif self.state not in [EntityState.PUNCH, EntityState.KICK]:
            self.state = EntityState.IDLE
        
        # Ограничение по экрану
        self.x = max(50, min(SCREEN_WIDTH - 50, self.x))
    
    def _handle_ai(self, player: Optional['Character'], particles: List):
        """Простой AI для противников"""
        if not player:
            return
            
        distance = abs(player.x - self.x)
        
        # Простейшее поведение
        if distance > 80:
            if player.x > self.x:
                self.x += self.speed * 0.7
                self.facing_right = True
            else:
                self.x -= self.speed * 0.7
                self.facing_right = False
            self.state = EntityState.WALK
        elif distance < 60:
            if player.x > self.x:
                self.x -= self.speed * 0.5
                self.facing_right = False
            else:
                self.x += self.speed * 0.5
                self.facing_right = True
        else:
            # Атака
            if self.attack_cooldown == 0 and random.random() < 0.05:
                attack_type = random.choice(['punch', 'kick'])
                self._perform_attack(attack_type, [player], particles)
            self.state = EntityState.IDLE
    
    def _perform_attack(self, attack_type: str, targets: List['Character'], particles: List):
        """Выполнение атаки"""
        if attack_type == 'punch':
            self.state = EntityState.PUNCH
            damage = self.damage * (1.5 if self.freeflow_active else 1.0)
            range_mult = 1.0
        else:
            self.state = EntityState.KICK
            damage = self.damage * 1.2 * (1.5 if self.freeflow_active else 1.0)
            range_mult = 1.3
        
        self.attack_cooldown = 20
        
        # Проверка попадания
        for target in targets:
            if target is self or target.hit_stun > 0 or target.knockdown_timer > 0:
                continue
                
            hit_range = 70 * range_mult
            if self.facing_right:
                hit_check = target.x > self.x and target.x - self.x < hit_range
            else:
                hit_check = target.x < self.x and self.x - target.x < hit_range
            
            vertical_check = abs(target.y - self.y) < 50
            
            if hit_check and vertical_check:
                # Попадание
                if target.block_active:
                    actual_damage = int(damage * target.block_damage_mult)
                    self._create_block_particles(target, particles)
                else:
                    actual_damage = int(damage)
                    target.hit_stun = 15
                    target.knockdown_timer = 10
                    self._create_hit_particles(target, particles)
                    
                    # Увеличение комбо
                    if self.is_player:
                        self.combo_count += 1
                        if self.combo_count >= 3 and not self.freeflow_active:
                            self.freeflow_active = True
                            self.freeflow_timer = 180  # 3 секунды
                
                target.health = max(0, target.health - actual_damage)
                target.invincible = 10
    
    def _create_hit_particles(self, target: 'Character', particles: List):
        """Создание эффектов при попадании"""
        for _ in range(15):
            particles.append(Particle(
                target.x + random.randint(-20, 20),
                target.y + random.randint(-40, 20),
                random.uniform(-8, 8),
                random.uniform(-10, 5),
                COLORS['hit_effect'],
                size=random.randint(4, 8),
                life=20
            ))
    
    def _create_block_particles(self, target: 'Character', particles: List):
        """Создание эффектов при блоке"""
        for _ in range(8):
            particles.append(Particle(
                target.x + random.randint(-20, 20),
                target.y + random.randint(-40, 20),
                random.uniform(-5, 5),
                random.uniform(-8, 2),
                COLORS['neon_blue'],
                size=random.randint(3, 6),
                life=15
            ))
    
    def _update_animation(self):
        """Обновление текущего кадра анимации"""
        anim_name = self.state.value
        if anim_name in self.animations:
            anim_frames = self.animations[anim_name]
            if len(anim_frames) > 0:
                self.animation_frame = (self.animation_frame + self.animation_speed) % len(anim_frames)
    
    def get_current_frame(self) -> AnimationFrame:
        """Получение текущего кадра анимации"""
        anim_name = self.state.value
        if anim_name in self.animations and self.animations[anim_name]:
            frame_idx = int(self.animation_frame) % len(self.animations[anim_name])
            return self.animations[anim_name][frame_idx]
        return AnimationFrame()
    
    def draw(self, screen: pygame.Surface):
        """Отрисовка персонажа"""
        frame = self.get_current_frame()
        
        # Мигание при неуязвимости
        if self.invincible > 0 and self.invincible % 4 < 2:
            return
        
        # Определение направления
        direction = 1 if self.facing_right else -1
        
        cx, cy = self.x, self.y
        
        # Свечение для Freeflow режима
        if self.freeflow_active:
            glow_surf = pygame.Surface((100, 150), pygame.SRCALPHA)
            pygame.draw.ellipse(glow_surf, (*COLORS['freeflow_glow'], 100), (0, 0, 100, 150))
            screen.blit(glow_surf, (cx - 50, cy - 100))
        
        # Отрисовка сегментов тела
        self._draw_body_part(screen, cx, cy, frame, direction)
    
    def _draw_body_part(self, screen: pygame.Surface, cx: float, cy: float, 
                       frame: AnimationFrame, direction: int):
        """Отрисовка сегментов тела персонажа"""
        
        # Тело
        body_x = cx + math.sin(math.radians(frame.body_angle)) * 5 * direction
        body_y = cy - 60
        body_rect = pygame.Rect(body_x - 15, body_y - 30, 30, 60)
        
        # Поворот тела
        body_surf = pygame.Surface((40, 70), pygame.SRCALPHA)
        pygame.draw.rect(body_surf, self.suit_color, (5, 5, 30, 60), border_radius=8)
        pygame.draw.rect(body_surf, self.skin_color, (10, 5, 20, 15), border_radius=5)
        
        # Детали костюма
        pygame.draw.line(body_surf, COLORS['neon_blue'] if self.is_player else COLORS['neon_red'], 
                        (20, 20), (20, 55), 2)
        
        rotated_body = pygame.transform.rotate(body_surf, frame.body_angle * direction)
        screen.blit(rotated_body, (body_x - rotated_body.get_width()//2, 
                                   body_y - rotated_body.get_height()//2))
        
        # Голова
        head_x = cx + frame.head_offset[0] * direction
        head_y = cy - 90 + frame.head_offset[1]
        pygame.draw.circle(screen, self.skin_color, (int(head_x), int(head_y)), 15)
        
        # Глаза (в стиле Replaced - светящиеся)
        eye_offset = 5 * direction
        pygame.draw.circle(screen, (0, 0, 0), (int(head_x + eye_offset), int(head_y - 3)), 4)
        pygame.draw.circle(screen, self.glow_color, (int(head_x + eye_offset + 1), int(head_y - 3)), 2)
        
        # Руки
        self._draw_arm(screen, cx, cy - 50, frame.arm_l_angle, frame.arm_l_extend, 
                      direction, is_left=True)
        self._draw_arm(screen, cx, cy - 50, frame.arm_r_angle, frame.arm_r_extend, 
                      direction, is_left=False)
        
        # Ноги
        self._draw_leg(screen, cx, cy, frame.leg_l_angle, direction, is_left=True)
        self._draw_leg(screen, cx, cy, frame.leg_r_angle, direction, is_left=False)
    
    def _draw_arm(self, screen: pygame.Surface, start_x: float, start_y: float,
                 angle: float, extend: float, direction: int, is_left: bool):
        """Отрисовка руки"""
        arm_length = 35 + extend
        end_x = start_x + math.cos(math.radians(angle)) * arm_length * direction
        end_y = start_y + math.sin(math.radians(angle)) * arm_length
        
        # Плечо
        pygame.draw.circle(screen, self.suit_color, (int(start_x), int(start_y)), 8)
        
        # Предплечье
        pygame.draw.line(screen, self.suit_color, 
                        (start_x, start_y), (end_x, end_y), 10)
        
        # Кулак
        pygame.draw.circle(screen, self.skin_color, (int(end_x), int(end_y)), 9)
        
        # Свечение кулака при атаке
        if abs(angle) > 60 and extend > 20:
            pygame.draw.circle(screen, self.glow_color, (int(end_x), int(end_y)), 12, 2)
    
    def _draw_leg(self, screen: pygame.Surface, start_x: float, start_y: float,
                 angle: float, direction: int, is_left: bool):
        """Отрисовка ноги"""
        leg_length = 40
        offset = -10 if is_left else 10
        end_x = start_x + offset + math.cos(math.radians(angle)) * leg_length * direction
        end_y = start_y + math.sin(math.radians(angle)) * leg_length
        
        # Бедро
        pygame.draw.line(screen, self.suit_color, 
                        (start_x + offset, start_y), (end_x, end_y), 12)
        
        # Стопа
        pygame.draw.ellipse(screen, (30, 30, 30), 
                           (int(end_x - 8), int(end_y - 4), 16, 8))


class Particle:
    """Класс частиц для эффектов"""
    
    def __init__(self, x: float, y: float, vx: float, vy: float, 
                 color: Tuple, size: int = 5, life: int = 30):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.3  # Гравитация
        self.life -= 1
        self.size = max(1, int(self.size * (self.life / self.max_life)))
    
    def draw(self, screen: pygame.Surface):
        alpha = int(255 * (self.life / self.max_life))
        surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), 
                          (self.size, self.size), self.size)
        screen.blit(surf, (self.x - self.size, self.y - self.size))


class Game:
    """Основной класс игры"""
    
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("REPLACED: Freeflow Fighting Arena")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.big_font = pygame.font.Font(None, 72)
        
        self.reset_game()
    
    def reset_game(self):
        """Сброс игры"""
        self.player = Character(SCREEN_WIDTH // 4, SCREEN_HEIGHT - 150, is_player=True)
        self.enemies: List[Character] = []
        self.particles: List[Particle] = []
        self.round = 1
        self.game_over = False
        self.victory = False
        self.spawn_enemies()
    
    def spawn_enemies(self):
        """Спавн врагов для текущего раунда"""
        self.enemies.clear()
        enemy_count = 1 + self.round  # Увеличивается с каждым раундом
        
        for i in range(enemy_count):
            x_pos = SCREEN_WIDTH * (0.5 + (i - enemy_count//2) * 0.2)
            enemy = Character(x_pos, SCREEN_HEIGHT - 150, is_player=False)
            enemy.health = 100 + self.round * 10  # Враги становятся сильнее
            enemy.damage = 8 + self.round * 2
            self.enemies.append(enemy)
    
    def handle_events(self):
        """Обработка событий"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_r and (self.game_over or self.victory):
                    self.reset_game()
        return True
    
    def update(self):
        """Обновление игрового состояния"""
        if self.game_over or self.victory:
            return
            
        keys = pygame.key.get_pressed()
        
        # Обновление игрока
        self.player.update(keys, self.enemies, self.particles)
        
        # Обновление врагов
        for enemy in self.enemies:
            enemy.update({}, [self.player], self.particles)
        
        # Обновление частиц
        for particle in self.particles[:]:
            particle.update()
            if particle.life <= 0:
                self.particles.remove(particle)
        
        # Проверка победы/поражения
        if self.player.health <= 0:
            self.game_over = True
        else:
            alive_enemies = [e for e in self.enemies if e.health > 0]
            if len(alive_enemies) == 0:
                if self.round >= 10:
                    self.victory = True
                else:
                    self.round += 1
                    self.player.health = min(100, self.player.health + 30)  # Лечение между раундами
                    self.spawn_enemies()
    
    def draw_background(self):
        """Отрисовка фона в стиле Replaced"""
        # Градиентный фон
        for y in range(SCREEN_HEIGHT):
            ratio = y / SCREEN_HEIGHT
            r = int(COLORS['background_dark'][0] * (1-ratio) + COLORS['background_mid'][0] * ratio)
            g = int(COLORS['background_dark'][1] * (1-ratio) + COLORS['background_mid'][1] * ratio)
            b = int(COLORS['background_dark'][2] * (1-ratio) + COLORS['background_mid'][2] * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))
        
        # Ринг
        floor_y = SCREEN_HEIGHT - 100
        pygame.draw.rect(self.screen, COLORS['ring_floor'], 
                        (0, floor_y, SCREEN_WIDTH, 100))
        
        # Линии на полу
        for i in range(0, SCREEN_WIDTH, 80):
            pygame.draw.line(self.screen, COLORS['neon_blue'], 
                           (i, floor_y), (i, SCREEN_HEIGHT), 2)
        
        # Канаты ринга
        for rope_y in [floor_y - 60, floor_y - 30]:
            pygame.draw.line(self.screen, COLORS['ring_rope'], 
                           (50, rope_y), (SCREEN_WIDTH - 50, rope_y), 4)
        
        # Стойки канатов
        for x in [50, SCREEN_WIDTH - 50]:
            pygame.draw.rect(self.screen, (80, 80, 80), (x - 10, floor_y - 80, 20, 80))
            pygame.draw.circle(self.screen, COLORS['neon_yellow'], (x, floor_y - 80), 8)
        
        # Неоновые вывески на фоне
        self._draw_neon_sign(200, 150, "FIGHT", COLORS['neon_pink'])
        self._draw_neon_sign(SCREEN_WIDTH - 200, 150, "ARENA", COLORS['neon_green'])
    
    def _draw_neon_sign(self, x: int, y: int, text: str, color: Tuple):
        """Отрисовка неоновой вывески"""
        text_surf = self.big_font.render(text, True, color)
        glow_surf = self.big_font.render(text, True, color)
        
        # Эффект свечения
        for offset in range(3, 0, -1):
            glow_surf = self.big_font.render(text, True, 
                                           tuple(min(255, c + 50) for c in color))
            self.screen.blit(glow_surf, (x - offset, y))
            self.screen.blit(glow_surf, (x + offset, y))
            self.screen.blit(glow_surf, (x, y - offset))
            self.screen.blit(glow_surf, (x, y + offset))
        
        self.screen.blit(text_surf, (x, y))
    
    def draw_ui(self):
        """Отрисовка интерфейса"""
        # Полоска здоровья игрока
        health_bar_width = 300
        health_bar_height = 25
        health_x = 50
        health_y = 50
        
        # Фон полоски
        pygame.draw.rect(self.screen, (50, 0, 0), 
                        (health_x, health_y, health_bar_width, health_bar_height), 
                        border_radius=5)
        
        # Текущее здоровье
        health_ratio = self.player.health / self.player.max_health
        health_color = COLORS['neon_green'] if health_ratio > 0.5 else COLORS['neon_red']
        pygame.draw.rect(self.screen, health_color, 
                        (health_x, health_y, int(health_bar_width * health_ratio), health_bar_height), 
                        border_radius=5)
        
        # Рамка
        pygame.draw.rect(self.screen, COLORS['ui_text'], 
                        (health_x, health_y, health_bar_width, health_bar_height), 
                        3, border_radius=5)
        
        # Текст
        player_text = self.font.render(f"PLAYER", True, COLORS['ui_text'])
        self.screen.blit(player_text, (health_x, health_y - 30))
        
        # Индикатор Freeflow
        if self.player.freeflow_active:
            freeflow_text = self.big_font.render("FREEFLOW!", True, COLORS['freeflow_glow'])
            glow_rect = freeflow_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
            
            # Свечение
            for offset in range(2, 0, -1):
                glow_surf = self.big_font.render("FREEFLOW!", True, COLORS['freeflow_glow'])
                self.screen.blit(glow_surf, (glow_rect.x - offset, glow_rect.y))
                self.screen.blit(glow_surf, (glow_rect.x + offset, glow_rect.y))
            
            self.screen.blit(freeflow_text, glow_rect)
        
        # Комбо счетчик
        if self.player.combo_count > 1:
            combo_text = self.font.render(f"COMBO x{self.player.combo_count}", 
                                         True, COLORS['neon_yellow'])
            self.screen.blit(combo_text, (health_x, health_y + 30))
        
        # Информация о раунде
        round_text = self.font.render(f"ROUND {self.round}", True, COLORS['ui_text'])
        round_rect = round_text.get_rect(center=(SCREEN_WIDTH // 2, 50))
        self.screen.blit(round_text, round_rect)
        
        # Здоровье врагов
        for i, enemy in enumerate(self.enemies):
            if enemy.health > 0:
                enemy_bar_width = 150
                enemy_bar_height = 15
                enemy_x = SCREEN_WIDTH - 200 - i * 160
                enemy_y = 50
                
                pygame.draw.rect(self.screen, (50, 0, 0), 
                               (enemy_x, enemy_y, enemy_bar_width, enemy_bar_height), 
                               border_radius=3)
                
                enemy_ratio = enemy.health / enemy.max_health
                pygame.draw.rect(self.screen, COLORS['neon_red'], 
                               (enemy_x, enemy_y, int(enemy_bar_width * enemy_ratio), enemy_bar_height), 
                               border_radius=3)
                
                pygame.draw.rect(self.screen, COLORS['ui_text'], 
                               (enemy_x, enemy_y, enemy_bar_width, enemy_bar_height), 
                               2, border_radius=3)
    
    def draw_game_over(self):
        """Отрисовка экрана проигрыша"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        
        game_over_text = self.big_font.render("GAME OVER", True, COLORS['neon_red'])
        restart_text = self.font.render("Press R to Restart", True, COLORS['ui_text'])
        
        self.screen.blit(game_over_text, 
                        game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)))
        self.screen.blit(restart_text, 
                        restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)))
    
    def draw_victory(self):
        """Отрисовка экрана победы"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        
        victory_text = self.big_font.render("VICTORY!", True, COLORS['neon_green'])
        restart_text = self.font.render("Press R to Play Again", True, COLORS['ui_text'])
        
        self.screen.blit(victory_text, 
                        victory_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)))
        self.screen.blit(restart_text, 
                        restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)))
    
    def draw(self):
        """Основная отрисовка"""
        self.draw_background()
        
        # Отрисовка персонажей
        for enemy in self.enemies:
            if enemy.health > 0:
                enemy.draw(self.screen)
        
        self.player.draw(self.screen)
        
        # Отрисовка частиц
        for particle in self.particles:
            particle.draw(self.screen)
        
        # Интерфейс
        self.draw_ui()
        
        # Экраны конца игры
        if self.game_over:
            self.draw_game_over()
        elif self.victory:
            self.draw_victory()
        
        pygame.display.flip()
    
    def run(self):
        """Игровой цикл"""
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
