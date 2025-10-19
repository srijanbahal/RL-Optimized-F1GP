"""
F1 Racing Simulator - Complete Admin Panel
Run: python race_game.py
"""

import math
import random
import pygame
from collections import deque
# import surf

# ---------- CONFIG ----------
SCREEN_W, SCREEN_H = 1920, 1080
WORLD_W, WORLD_H = 3000, 2000
FPS = 60

NUM_AI = 9  # Total 10 cars
LAPS_TO_FINISH = 5

# Car physics
MAX_SPEED = 8.5
ACCEL = 0.22
BRAKE = 0.35
TURN_SPEED = 2.8
DRAG = 0.992

# Tire compounds with full simulation
TIRE_COMPOUNDS = {
    'soft': {
        'wear_rate': 0.0008,
        'grip': 1.25,
        'temp_optimal': 90,
        'temp_range': 12,
        'heat_rate': 1.8,
        'color': (255, 50, 50)
    },
    'medium': {
        'wear_rate': 0.0004,
        'grip': 1.0,
        'temp_optimal': 80,
        'temp_range': 18,
        'heat_rate': 1.2,
        'color': (255, 200, 0)
    },
    'hard': {
        'wear_rate': 0.0002,
        'grip': 0.85,
        'temp_optimal': 70,
        'temp_range': 25,
        'heat_rate': 0.8,
        'color': (220, 220, 220)
    },
}

# Engine modes
ENGINE_MODES = {
    'qualifying': {'power': 1.3, 'fuel_rate': 2.5},
    'race': {'power': 1.0, 'fuel_rate': 1.0},
    'conservation': {'power': 0.75, 'fuel_rate': 0.6},
}

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_BG = (10, 12, 18)
PANEL_BG = (20, 25, 35)
HEADER_BG = (25, 30, 42)
GRAY = (120, 120, 120)
DARK_GRAY = (60, 65, 75)
GREEN = (46, 204, 113)
DARK_GREEN = (39, 174, 96)
GRASS_GREEN = (118, 188, 74)
RED = (231, 76, 60)
YELLOW = (241, 196, 15)
BLUE = (52, 152, 219)
ORANGE = (230, 126, 34)
PURPLE = (155, 89, 182)
LIGHT_GRAY = (189, 195, 199)
TRACK_GRAY = (149, 165, 166)
SAND_YELLOW = (230, 218, 158)

pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("F1 Race Control - Admin Panel")
clock = pygame.time.Clock()
font_xs = pygame.font.SysFont("Consolas", 12)
font_sm = pygame.font.SysFont("Consolas", 14)
font_md = pygame.font.SysFont("Consolas", 16)
font_lg = pygame.font.SysFont("Consolas", 18, bold=True)
font_xl = pygame.font.SysFont("Consolas", 22, bold=True)

def clamp(x, a, b):
    return max(a, min(b, x))

def lerp(a, b, t):
    return a + (b - a) * t

# ---------- Track (Figure-8 Style) ----------
class Track:
    def __init__(self):
        self.center_x = WORLD_W // 2
        self.center_y = WORLD_H // 2
        
        # ========== MODIFIED TRACK GENERATION LOGIC START ==========
        # Define the new track shape with a series of control points
        # These points approximate the shape from the user's image
        control_points = [
            (1000, 1450), # Start/Finish line area
            (1800, 1450), # End of main straight
            (2200, 1300), # Start of long right turn
            (2350, 1000), # Apex 1
            (2200, 700),  # End of long right turn
            (1800, 600),  # Top straight
            (1400, 600),  # End of top straight
            (1100, 750),  # Start of left complex
            (1000, 1000), # Midpoint of left complex
            (1100, 1250), # End of left complex, leads back to straight
        ]

        # Generate more waypoints by interpolating between control points for smoother curves
        self.waypoints = []
        num_segments = len(control_points)
        points_per_segment = 12 # Increase for even smoother curves

        for i in range(num_segments):
            p1 = control_points[i]
            p2 = control_points[(i + 1) % num_segments] # Loop back to the start
            for j in range(points_per_segment):
                t = j / points_per_segment
                x = lerp(p1[0], p2[0], t)
                y = lerp(p1[1], p2[1], t)
                self.waypoints.append((x, y))
        # ========== MODIFIED TRACK GENERATION LOGIC END ==========

        # Track boundaries
        self.track_width = 180
        self.barrier_width = 25
        
        # Pit lane (re-positioned along the new start/finish straight)
        self.pit_rect = pygame.Rect(1100, 1600, 600, 80)
        
        # Start/finish line position
        self.start_line = (self.waypoints[0][0], self.waypoints[0][1])

    def draw(self, surf, cam_offset):
        # Draw grass background
        surf.fill(GRASS_GREEN)
        
        # Draw sand runoff areas
        for i in range(len(self.waypoints)):
            x, y = self.waypoints[i]
            pygame.draw.circle(surf, SAND_YELLOW,
                             (int(x - cam_offset[0]), int(y - cam_offset[1])),
                             self.track_width + 50, 0)
        
        # Draw track surface by connecting waypoints
        pygame.draw.lines(surf, TRACK_GRAY, False,
                          [(p[0] - cam_offset[0], p[1] - cam_offset[1]) for p in self.waypoints],
                          self.track_width)
        # Connect the last point to the first to close the loop
        p1 = self.waypoints[-1]
        p2 = self.waypoints[0]
        pygame.draw.line(surf, TRACK_GRAY,
                           (p1[0] - cam_offset[0], p1[1] - cam_offset[1]),
                           (p2[0] - cam_offset[0], p2[1] - cam_offset[1]),
                           self.track_width)
        
        # Draw outer barriers (red/white)
        for i in range(len(self.waypoints)):
            p1 = self.waypoints[i]
            p2 = self.waypoints[(i + 1) % len(self.waypoints)]
            
            # Calculate outer edge normal
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            mag = math.hypot(dx, dy)
            if mag == 0: continue
            
            nx, ny = -dy / mag, dx / mag # Normal vector
            offset = self.track_width / 2 + self.barrier_width / 2
            
            x1_outer = p1[0] - cam_offset[0] + nx * offset
            y1_outer = p1[1] - cam_offset[1] + ny * offset
            x2_outer = p2[0] - cam_offset[0] + nx * offset
            y2_outer = p2[1] - cam_offset[1] + ny * offset
            
            pygame.draw.line(surf, RED if i % 8 < 4 else WHITE,
                           (x1_outer, y1_outer),
                           (x2_outer, y2_outer),
                           self.barrier_width)

        # Draw center line dashes
        for i in range(0, len(self.waypoints), 4):
            x, y = self.waypoints[i]
            pygame.draw.circle(surf, WHITE,
                             (int(x - cam_offset[0]), int(y - cam_offset[1])), 3)
        
        # Draw start/finish line (checkered pattern)
        sx, sy = self.start_line
        for i in range(-3, 4):
            for j in range(10):
                color = BLACK if (i + j) % 2 == 0 else WHITE
                rect = pygame.Rect(sx - cam_offset[0] + i * 15 - 50,
                                     sy - cam_offset[1] + j * 10 - 50, 14, 10)
                pygame.draw.rect(surf, color, rect)
        
        # Draw pit lane
        pit_rect_screen = self.pit_rect.move(-cam_offset[0], -cam_offset[1])
        pygame.draw.rect(surf, (100, 100, 110), pit_rect_screen)
        pygame.draw.rect(surf, YELLOW, pit_rect_screen, 4)

# ---------- Car ----------
class Car:
    def __init__(self, id, x, y, color, team_name):
        self.id = id
        self.team_name = team_name
        self.x = x
        self.y = y
        self.angle = 0
        self.speed = 0.0
        self.color = color
        self.width = 20
        self.length = 36
        
        # Race position
        self.lap = 0
        self.finished = False
        self.position = 1
        self.total_time = 0.0
        self.current_lap_time = 0.0
        self.best_lap = None
        self.last_lap_time = None
        self.sector_times = [0.0, 0.0, 0.0]
        
        # Tire system
        self.tire_compound = random.choice(['soft', 'medium', 'hard'])
        self.tire_wear = 0.0
        self.tire_temp = 45.0
        self.tire_age = 0  # laps on current tires
        
        # Engine & fuel
        self.fuel = 1.0
        self.fuel_load = 1.0  # Starting fuel weight
        self.engine_mode = 'race'
        self.ers_battery = 1.0
        self.ers_deployment = 0.0
        
        # Brakes & temperature
        self.brake_temp = 40.0
        self.engine_temp = 85.0
        
        # DRS
        self.drs_available = False
        self.drs_active = False
        self.drs_cooldown = 0.0
        
        # Aerodynamics
        self.downforce_level = 5  # 1-10 scale
        self.in_slipstream = False
        
        # Pit stop
        self.pit_stops = 0
        self.in_pit = False
        self.pit_timer = 0.0
        
        # Penalties
        self.penalties = 0.0
        
        # Track position
        self.waypoint_index = 0
        self._last_pass = None

    def get_total_weight(self):
        """Calculate current car weight including fuel"""
        base_weight = 798  # kg minimum F1 weight
        fuel_weight = self.fuel * 110  # ~110kg full tank
        return base_weight + fuel_weight

    def get_grip_multiplier(self):
        """Calculate grip based on tire condition and temperature"""
        compound = TIRE_COMPOUNDS[self.tire_compound]
        optimal_temp = compound['temp_optimal']
        temp_range = compound['temp_range']
        
        # Tire wear reduces grip (up to 40% loss)
        wear_penalty = self.tire_wear * 0.4
        
        # Temperature affects grip significantly
        temp_diff = abs(self.tire_temp - optimal_temp)
        if temp_diff > temp_range:
            temp_penalty = 0.4  # Cold or overheated tires lose 60% grip
        else:
            temp_penalty = (temp_diff / temp_range) * 0.25
        
        base_grip = compound['grip']
        total_grip = base_grip * (1.0 - temp_penalty) * (1.0 - wear_penalty)
        
        # Downforce adds mechanical grip
        downforce_bonus = self.downforce_level * 0.02
        
        return max(0.3, total_grip + downforce_bonus)

    def get_power_multiplier(self):
        """Calculate power output based on engine mode and ERS"""
        mode = ENGINE_MODES[self.engine_mode]
        base_power = mode['power']
        
        # Fuel weight affects acceleration
        weight_factor = 798 / self.get_total_weight()
        
        # ERS deployment adds power
        ers_boost = self.ers_deployment * 0.3
        
        # DRS reduces drag, increasing top speed
        drs_boost = 0.15 if self.drs_active else 0.0
        
        # Slipstream effect
        slipstream_boost = 0.08 if self.in_slipstream else 0.0
        
        return base_power * weight_factor + ers_boost + drs_boost + slipstream_boost

    def update(self, dt, action, track, all_cars):
        if self.finished:
            return
        
        throttle = clamp(action.get('throttle', 0.0), -1.0, 1.0)
        steer = clamp(action.get('steer', 0.0), -1.0, 1.0)
        use_ers = action.get('use_ers', False)
        
        # DRS logic - available when close to car ahead on straight
        if self.drs_cooldown > 0:
            self.drs_cooldown -= dt
        
        if abs(steer) < 0.2 and self.speed > MAX_SPEED * 0.6:
            # Check if within 1 second of car ahead
            gap_to_ahead = self._get_gap_to_ahead(all_cars)
            self.drs_available = gap_to_ahead < 1.0 and self.drs_cooldown <= 0
        else:
            self.drs_available = False
        
        self.drs_active = self.drs_available and action.get('use_drs', False)
        
        # ERS deployment
        if use_ers and self.ers_battery > 0.05:
            self.ers_deployment = min(1.0, self.ers_deployment + dt * 2.0)
            self.ers_battery -= dt * 0.15
        else:
            self.ers_deployment = max(0.0, self.ers_deployment - dt * 3.0)
        
        # ERS recovery during braking
        if throttle < -0.2:
            self.ers_battery = min(1.0, self.ers_battery + abs(throttle) * dt * 0.08)
        
        # Speed physics with all factors
        power = self.get_power_multiplier()
        grip = self.get_grip_multiplier()
        
        if throttle > 0:
            self.speed += throttle * ACCEL * power
        elif throttle < 0:
            self.speed += throttle * BRAKE * grip
            # Brake temperature
            self.brake_temp += abs(throttle) * 4.0 * self.speed / MAX_SPEED
        
        # Brake fade when overheated
        if self.brake_temp > 120:
            self.speed *= 0.998  # Reduced braking efficiency
        
        self.speed *= DRAG
        
        # Top speed affected by downforce and fuel
        max_speed_adjusted = MAX_SPEED * (1.0 - self.downforce_level * 0.02)
        self.speed = clamp(self.speed, 0.0, max_speed_adjusted)
        
        # Steering with grip and speed
        steer_scale = (self.speed / MAX_SPEED) * TURN_SPEED * grip
        self.angle += steer * steer_scale
        
        # Position update
        rad = math.radians(self.angle)
        self.x += math.cos(rad) * self.speed
        self.y += math.sin(rad) * self.speed
        
        # Tire temperature simulation
        compound = TIRE_COMPOUNDS[self.tire_compound]
        corner_intensity = abs(steer) * (self.speed / MAX_SPEED)
        heat_generation = compound['heat_rate'] * (0.3 + corner_intensity * 2.5 + abs(throttle) * 0.5)
        self.tire_temp += heat_generation * self.speed / MAX_SPEED
        self.tire_temp *= 0.985  # Natural cooling
        self.tire_temp = clamp(self.tire_temp, 40, 125)
        
        # Tire wear
        wear_rate = TIRE_COMPOUNDS[self.tire_compound]['wear_rate']
        wear_multiplier = 1.0 + corner_intensity * 1.5 + (self.speed / MAX_SPEED) * 0.5
        if self.tire_temp > 105:  # Overheating increases wear
            wear_multiplier *= 1.8
        self.tire_wear += wear_rate * wear_multiplier
        self.tire_wear = clamp(self.tire_wear, 0.0, 1.0)
        
        # Brake temperature
        self.brake_temp *= 0.96
        self.brake_temp = clamp(self.brake_temp, 40, 180)
        
        # Engine temperature
        self.engine_temp = 85 + (self.speed / MAX_SPEED) * 25 + (throttle if throttle > 0 else 0) * 15
        self.engine_temp = clamp(self.engine_temp, 85, 125)
        
        # Fuel consumption
        fuel_rate = ENGINE_MODES[self.engine_mode]['fuel_rate']
        self.fuel -= 0.0004 * fuel_rate * (0.5 + self.speed / MAX_SPEED + abs(throttle) * 0.5)
        self.fuel = clamp(self.fuel, 0.0, 1.0)
        
        # Out of fuel - slow down
        if self.fuel <= 0.01:
            self.speed *= 0.95
        
        # Update timers
        self.current_lap_time += dt
        self.total_time += dt
        
        # World boundaries
        if self.x < 50 or self.x > WORLD_W - 50 or self.y < 50 or self.y > WORLD_H - 50:
            self.x = clamp(self.x, 50, WORLD_W - 50)
            self.y = clamp(self.y, 50, WORLD_H - 50)
            self.speed *= 0.6  # Penalty for going off track

    def _get_gap_to_ahead(self, all_cars):
        """Calculate time gap to car ahead"""
        # Simplified - in reality would need to calculate based on track position
        return random.uniform(0.5, 2.0)  # Placeholder

    def handle_pit_stop(self, track):
        """Handle pit stop logic"""
        if not track.pit_rect.collidepoint(self.x, self.y):
            self.in_pit = False
            return
        
        if not self.in_pit:
            self.in_pit = True
            self.pit_timer = 0.0
            self.pit_stops += 1
        
        self.pit_timer += 1/FPS
        self.speed *= 0.3  # Pit lane speed limit
        
        # Pit stop takes 2-3 seconds
        if self.pit_timer > 2.5:
            self.fuel = 1.0
            self.tire_wear = 0.0
            self.tire_temp = 50.0
            self.tire_age = 0
            self.in_pit = False

    def draw(self, surf, cam_offset):
        # Car body
        car_surf = pygame.Surface((self.length, self.width), pygame.SRCALPHA)
        car_surf.fill((0, 0, 0, 0))
        
        # Main body
        pygame.draw.rect(car_surf, self.color, pygame.Rect(0, 0, self.length, self.width), border_radius=4)
        
        # Cockpit
        pygame.draw.rect(car_surf, (30, 30, 30),
                        pygame.Rect(self.length * 0.4, 4, self.length * 0.25, self.width - 8),
                        border_radius=2)
        
        # Front wing
        pygame.draw.rect(car_surf, BLACK, pygame.Rect(0, 2, 6, self.width - 4))
        
        # Rear wing
        pygame.draw.rect(car_surf, BLACK, pygame.Rect(self.length - 6, 2, 6, self.width - 4))
        
        # DRS indicator (if active)
        if self.drs_active:
            pygame.draw.rect(car_surf, GREEN, pygame.Rect(self.length - 8, 4, 4, self.width - 8))
        
        # Tire compound indicator (small dots on sides)
        tire_color = TIRE_COMPOUNDS[self.tire_compound]['color']
        pygame.draw.circle(car_surf, tire_color, (8, 3), 2)
        pygame.draw.circle(car_surf, tire_color, (8, self.width - 3), 2)
        
        rotated = pygame.transform.rotate(car_surf, -self.angle)
        rect = rotated.get_rect(center=(self.x - cam_offset[0], self.y - cam_offset[1]))
        surf.blit(rotated, rect.topleft)
        
        # Position number above car
        pos_text = font_xs.render(str(self.position), True, WHITE)
        surf.blit(pos_text, (self.x - cam_offset[0] - 5, self.y - cam_offset[1] - 25))

# ---------- AI Controller ----------
class AIController:
    def __init__(self, car, waypoints):
        self.car = car
        self.waypoints = waypoints
        self.idx = 0
        self.skill = random.uniform(0.75, 0.95)  # AI skill level
        self.aggression = random.uniform(0.6, 0.9)
        self.pit_strategy = random.choice(['aggressive', 'standard', 'conservative'])

    def step(self, all_cars):
        # Update waypoint target
        tx, ty = self.waypoints[self.idx]
        cx, cy = self.car.x, self.car.y
        
        if math.hypot(tx - cx, ty - cy) < 120: # Increased distance to switch waypoints for smoother turning
            self.idx = (self.idx + 1) % len(self.waypoints)
            tx, ty = self.waypoints[self.idx]
        
        self.car.waypoint_index = self.idx
        
        # Calculate steering
        desired = math.degrees(math.atan2(ty - cy, tx - cx))
        diff = (desired - self.car.angle + 540) % 360 - 180
        steer = clamp(diff / 45.0, -1.0, 1.0) * self.skill # Reduced sensitivity for wider turns
        
        # Throttle control based on corner sharpness
        if abs(diff) > 45:
            throttle = 0.5 * self.aggression
        elif abs(diff) > 20:
            throttle = 0.8 * self.aggression
        else:
            throttle = 1.0 * self.aggression
        
        # Add some variation
        throttle *= random.uniform(0.95, 1.0)
        
        # Pit stop decision
        pit = False
        if self.car.tire_wear > 0.7 or self.car.fuel < 0.25:
            pit = True
        
        # ERS usage
        use_ers = self.car.speed > MAX_SPEED * 0.7 and self.car.ers_battery > 0.3
        
        # DRS usage
        use_drs = self.car.drs_available
        
        # Engine mode strategy
        if self.car.fuel < 0.3:
            self.car.engine_mode = 'conservation'
        elif self.car.lap == 0:
            self.car.engine_mode = 'qualifying'
        else:
            self.car.engine_mode = 'race'
        
        return {
            'throttle': throttle,
            'steer': steer,
            'pit': pit,
            'use_ers': use_ers,
            'use_drs': use_drs
        }

# ---------- Simulation ----------
class SimulationManager:
    def __init__(self):
        self.track = Track()
        
        # Team colors and names
        teams = [
            ("Red Bull", (30, 65, 174)),
            ("Ferrari", (220, 0, 0)),
            ("Mercedes", (0, 210, 190)),
            ("McLaren", (255, 135, 0)),
            ("Aston Martin", (0, 111, 98)),
            ("Alpine", (34, 147, 209)),
            ("Williams", (0, 82, 180)),
            ("AlphaTauri", (43, 69, 98)),
            ("Alfa Romeo", (155, 0, 28)),
            ("Haas", (180, 180, 180))
        ]
        
        self.cars = []
        
        # Spawn cars at start line with staggered positions
        start_x, start_y = self.track.start_line
        for i in range(NUM_AI + 1):
            team_name, color = teams[i % len(teams)]
            # Grid formation (2 by 2)
            row = i // 2
            col = i % 2
            offset_x = -row * 60
            offset_y = (col - 0.5) * 45
            
            car_id = f"P1" if i == 0 else f"AI{i}"
            car = Car(car_id, start_x + offset_x, start_y + offset_y, color, team_name)
            car.angle = 0  # Facing right direction along the new straight
            self.cars.append(car)
        
        # Create AI controllers
        self.ai_ctrl = [AIController(c, self.track.waypoints) for c in self.cars if c.id.startswith("AI")]
        
        self.finished_order = []
        self.time = 0.0
        self.race_started = False
        self.start_countdown = 5.0
        
        # Weather and track conditions
        self.track_temp = 35.0
        self.air_temp = 25.0
        self.weather = "Clear"

    def step(self, dt, player_action):
        # Countdown before race start
        if not self.race_started:
            self.start_countdown -= dt
            if self.start_countdown <= 0:
                self.race_started = True
            else:
                return  # Don't update cars during countdown
        
        # Update all cars
        self.cars[0].update(dt, player_action, self.track, self.cars)
        self.cars[0].handle_pit_stop(self.track)
        
        for i, ai_car in enumerate(self.cars[1:]):
            ctrl = self.ai_ctrl[i]
            action = ctrl.step(self.cars)
            ai_car.update(dt, action, self.track, self.cars)
            ai_car.handle_pit_stop(self.track)
        
        # Lap detection
        for car in self.cars:
            if car.finished:
                continue
            
            sx, sy = self.track.start_line
            dist_to_line = math.hypot(car.x - sx, car.y - sy)
            
            # Check if car is near the start line and moving in the correct direction
            is_near_line = dist_to_line < 100
            moving_correctly = car.x < sx + 50 # Ensure car has passed the line
            
            if is_near_line and moving_correctly:
                if car._last_pass is None or self.time - car._last_pass > 10.0:
                    car._last_pass = self.time
                    
                    if car.lap > 0:  # Don't count first crossing
                        car.last_lap_time = car.current_lap_time
                        if car.best_lap is None or car.current_lap_time < car.best_lap:
                            car.best_lap = car.current_lap_time
                        car.current_lap_time = 0.0
                        car.tire_age += 1
                    
                    car.lap += 1
                    
                    if car.lap > LAPS_TO_FINISH:
                        car.finished = True
                        self.finished_order.append((len(self.finished_order) + 1, car.id, car.total_time))
        
        # Update positions
        leaderboard = self.get_leaderboard()
        for i, car in enumerate(leaderboard):
            car.position = i + 1
        
        self.time += dt

    def get_leaderboard(self):
        """Sort cars by race position"""
        def race_key(c):
            # Finished cars first, then by laps, then by waypoint progress
            progress_on_lap = c.waypoint_index / len(self.track.waypoints)
            return (-c.lap, -progress_on_lap)
        
        sorted_cars = sorted([car for car in self.cars if not car.finished], key=race_key)
        finished_cars = sorted([car for car in self.cars if car.finished], key=lambda c: c.total_time)
        return finished_cars + sorted_cars


    def draw(self, surf, cam_offset):
        self.track.draw(surf, cam_offset)
        
        # Draw cars sorted by y position (back to front)
        sorted_cars = sorted(self.cars, key=lambda c: c.y)
        for car in sorted_cars:
            car.draw(surf, cam_offset)

# ---------- UI Panels ----------
def draw_header(surf, sim):
    """Top header with race info"""
    header_height = 70
    pygame.draw.rect(surf, HEADER_BG, pygame.Rect(0, 0, SCREEN_W, header_height))
    pygame.draw.line(surf, YELLOW, (0, header_height), (SCREEN_W, header_height), 3)
    
    # Race title
    title = font_xl.render("F1 RACE CONTROL - ADMIN PANEL", True, YELLOW)
    surf.blit(title, (20, 15))
    
    # Race time and lap
    race_time = f"Race Time: {sim.time:.1f}s"
    laps_info = f"Laps: {LAPS_TO_FINISH}"
    surf.blit(font_lg.render(race_time, True, WHITE), (20, 42))
    surf.blit(font_lg.render(laps_info, True, WHITE), (250, 42))
    
    # Weather
    weather_text = f"Weather: {sim.weather} | Track: {sim.track_temp}°C | Air: {sim.air_temp}°C"
    surf.blit(font_md.render(weather_text, True, LIGHT_GRAY), (450, 45))
    
    # Countdown
    if not sim.race_started:
        countdown_text = f"RACE STARTS IN: {max(0, sim.start_countdown):.1f}"
        text = font_xl.render(countdown_text, True, RED)
        surf.blit(text, (SCREEN_W - 450, 20))

def draw_leaderboard(surf, sim):
    """Left panel - Leaderboard"""
    panel_w = 380
    panel_h = SCREEN_H - 90
    panel_x = 10
    panel_y = 80
    
    pygame.draw.rect(surf, PANEL_BG, pygame.Rect(panel_x, panel_y, panel_w, panel_h), border_radius=8)
    pygame.draw.rect(surf, YELLOW, pygame.Rect(panel_x, panel_y, panel_w, panel_h), 2, border_radius=8)
    
    # Header
    header_text = font_lg.render("LIVE STANDINGS", True, YELLOW)
    surf.blit(header_text, (panel_x + 15, panel_y + 10))
    
    y_pos = panel_y + 45
    leaderboard = sim.get_leaderboard()
    
    for i, car in enumerate(leaderboard[:20]): # Show more cars if possible
        # Position number background
        pos_color = YELLOW if i == 0 else ORANGE if i == 1 else (200, 140, 30) if i == 2 else DARK_GRAY
        pygame.draw.rect(surf, pos_color, pygame.Rect(panel_x + 15, y_pos, 30, 30), border_radius=4)
        
        # Position number
        pos_text = font_md.render(str(i + 1), True, BLACK if i < 3 else WHITE)
        surf.blit(pos_text, (panel_x + 23 - (4 if i+1 < 10 else 8), y_pos + 7))
        
        # Car ID and team
        car_text = font_md.render(f"{car.id} - {car.team_name}", True, car.color)
        surf.blit(car_text, (panel_x + 55, y_pos + 2))
        
        # Lap info
        lap_text = font_sm.render(f"Lap {car.lap}/{LAPS_TO_FINISH}", True, LIGHT_GRAY)
        surf.blit(lap_text, (panel_x + 55, y_pos + 18))
        
        # Status indicators
        status_x = panel_x + 280
        if car.in_pit:
            pygame.draw.circle(surf, YELLOW, (status_x, y_pos + 15), 5)
            surf.blit(font_xs.render("PIT", True, YELLOW), (status_x + 10, y_pos + 10))
        elif car.drs_active:
            pygame.draw.circle(surf, GREEN, (status_x, y_pos + 15), 5)
            surf.blit(font_xs.render("DRS", True, GREEN), (status_x + 10, y_pos + 10))
        elif car.finished:
            surf.blit(font_xs.render("FIN", True, GREEN), (status_x + 10, y_pos + 10))
        
        y_pos += 38

def draw_telemetry(surf, sim):
    """Right panel - Detailed telemetry for selected car"""
    panel_w = 420
    panel_h = SCREEN_H - 90
    panel_x = SCREEN_W - panel_w - 10
    panel_y = 80
    
    pygame.draw.rect(surf, PANEL_BG, pygame.Rect(panel_x, panel_y, panel_w, panel_h), border_radius=8)
    pygame.draw.rect(surf, YELLOW, pygame.Rect(panel_x, panel_y, panel_w, panel_h), 2, border_radius=8)
    
    # Header
    header_text = font_lg.render("CAR TELEMETRY", True, YELLOW)
    surf.blit(header_text, (panel_x + 15, panel_y + 10))
    
    # Display telemetry for leader (or could be selected car)
    leaderboard = sim.get_leaderboard()
    if not leaderboard: return
    car = leaderboard[0]
    
    y_pos = panel_y + 45
    
    # Car info section
    surf.blit(font_md.render(f"Car: {car.id} - {car.team_name}", True, car.color), (panel_x + 15, y_pos))
    y_pos += 25
    surf.blit(font_sm.render(f"Position: {car.position} | Lap: {car.lap}/{LAPS_TO_FINISH}", True, WHITE),
              (panel_x + 15, y_pos))
    y_pos += 35
    
    # Speed and performance
    draw_telemetry_row(surf, panel_x + 15, y_pos, "Speed", f"{car.speed*20:.1f} KPH", # Scaled for display
                       car.speed / MAX_SPEED, GREEN)
    y_pos += 35
    
    # Throttle position (simulated from speed)
    throttle_val = min(1.0, car.speed / (MAX_SPEED * 0.8))
    draw_telemetry_row(surf, panel_x + 15, y_pos, "Throttle", f"{throttle_val*100:.0f}%",
                       throttle_val, GREEN)
    y_pos += 35
    
    # Tire section
    pygame.draw.line(surf, DARK_GRAY, (panel_x + 15, y_pos), (panel_x + panel_w - 15, y_pos), 1)
    y_pos += 10
    surf.blit(font_md.render("TIRES", True, YELLOW), (panel_x + 15, y_pos))
    y_pos += 25
    
    tire_color = TIRE_COMPOUNDS[car.tire_compound]['color']
    surf.blit(font_sm.render(f"Compound: {car.tire_compound.upper()}", True, tire_color),
              (panel_x + 15, y_pos))
    surf.blit(font_sm.render(f"Age: {car.tire_age} laps", True, LIGHT_GRAY),
              (panel_x + 220, y_pos))
    y_pos += 25
    
    wear_color = GREEN if car.tire_wear < 0.3 else YELLOW if car.tire_wear < 0.6 else RED
    draw_telemetry_row(surf, panel_x + 15, y_pos, "Wear", f"{car.tire_wear*100:.1f}%",
                       car.tire_wear, wear_color)
    y_pos += 35
    
    temp_color = GREEN if 70 <= car.tire_temp <= 95 else YELLOW if 60 <= car.tire_temp <= 105 else RED
    draw_telemetry_row(surf, panel_x + 15, y_pos, "Temp", f"{car.tire_temp:.1f}°C",
                       (car.tire_temp - 40) / 80, temp_color)
    y_pos += 40
    
    # Fuel section
    pygame.draw.line(surf, DARK_GRAY, (panel_x + 15, y_pos), (panel_x + panel_w - 15, y_pos), 1)
    y_pos += 10
    surf.blit(font_md.render("FUEL & POWER", True, YELLOW), (panel_x + 15, y_pos))
    y_pos += 25
    
    fuel_color = GREEN if car.fuel > 0.3 else YELLOW if car.fuel > 0.15 else RED
    draw_telemetry_row(surf, panel_x + 15, y_pos, "Fuel", f"{car.fuel*100:.1f}%",
                       car.fuel, fuel_color)
    y_pos += 35
    
    surf.blit(font_sm.render(f"Engine Mode: {car.engine_mode.upper()}", True, WHITE),
              (panel_x + 15, y_pos))
    y_pos += 25
    
    ers_color = GREEN if car.ers_battery > 0.5 else YELLOW if car.ers_battery > 0.2 else RED
    draw_telemetry_row(surf, panel_x + 15, y_pos, "ERS", f"{car.ers_battery*100:.0f}%",
                       car.ers_battery, ers_color)
    y_pos += 40
    
    # Temperature section
    pygame.draw.line(surf, DARK_GRAY, (panel_x + 15, y_pos), (panel_x + panel_w - 15, y_pos), 1)
    y_pos += 10
    surf.blit(font_md.render("TEMPERATURES", True, YELLOW), (panel_x + 15, y_pos))
    y_pos += 25
    
    brake_color = GREEN if car.brake_temp < 100 else YELLOW if car.brake_temp < 130 else RED
    draw_telemetry_row(surf, panel_x + 15, y_pos, "Brakes", f"{car.brake_temp:.1f}°C",
                       (car.brake_temp - 40) / 140, brake_color)
    y_pos += 35
    
    engine_color = GREEN if car.engine_temp < 105 else YELLOW if car.engine_temp < 115 else RED
    draw_telemetry_row(surf, panel_x + 15, y_pos, "Engine", f"{car.engine_temp:.1f}°C",
                       (car.engine_temp - 85) / 40, engine_color)
    y_pos += 40
    
    # Lap times section
    pygame.draw.line(surf, DARK_GRAY, (panel_x + 15, y_pos), (panel_x + panel_w - 15, y_pos), 1)
    y_pos += 10
    surf.blit(font_md.render("LAP TIMES", True, YELLOW), (panel_x + 15, y_pos))
    y_pos += 25
    
    surf.blit(font_sm.render(f"Current: {car.current_lap_time:.2f}s", True, WHITE),
              (panel_x + 15, y_pos))
    y_pos += 20
    
    if car.last_lap_time:
        surf.blit(font_sm.render(f"Last Lap: {car.last_lap_time:.2f}s", True, LIGHT_GRAY),
                  (panel_x + 15, y_pos))
    y_pos += 20
    
    if car.best_lap:
        surf.blit(font_sm.render(f"Best Lap: {car.best_lap:.2f}s", True, GREEN),
                  (panel_x + 15, y_pos))
    y_pos += 20
    
    surf.blit(font_sm.render(f"Total Time: {car.total_time:.2f}s", True, LIGHT_GRAY),
              (panel_x + 15, y_pos))
    y_pos += 30
    
    # DRS and Aerodynamics
    pygame.draw.line(surf, DARK_GRAY, (panel_x + 15, y_pos), (panel_x + panel_w - 15, y_pos), 1)
    y_pos += 10
    surf.blit(font_md.render("AERODYNAMICS", True, YELLOW), (panel_x + 15, y_pos))
    y_pos += 25
    
    drs_status = "ACTIVE" if car.drs_active else ("AVAILABLE" if car.drs_available else "DISABLED")
    drs_color = GREEN if car.drs_active else YELLOW if car.drs_available else GRAY
    surf.blit(font_sm.render(f"DRS: {drs_status}", True, drs_color), (panel_x + 15, y_pos))
    y_pos += 20
    
    surf.blit(font_sm.render(f"Downforce Level: {car.downforce_level}/10", True, WHITE),
              (panel_x + 15, y_pos))
    y_pos += 25
    
    # Pit stops
    surf.blit(font_sm.render(f"Pit Stops: {car.pit_stops}", True, ORANGE),
              (panel_x + 15, y_pos))

def draw_telemetry_row(surf, x, y, label, value, progress, color):
    """Draw a telemetry row with label, value, and progress bar"""
    # Label
    surf.blit(font_sm.render(label, True, LIGHT_GRAY), (x, y))
    
    # Value
    surf.blit(font_sm.render(value, True, WHITE), (x + 120, y))
    
    # Progress bar
    bar_x = x
    bar_y = y + 18
    bar_w = 380
    bar_h = 8
    
    pygame.draw.rect(surf, DARK_GRAY, pygame.Rect(bar_x, bar_y, bar_w, bar_h), border_radius=4)
    pygame.draw.rect(surf, color, pygame.Rect(bar_x, bar_y, int(bar_w * clamp(progress, 0, 1)), bar_h),
                     border_radius=4)

def draw_race_stats(surf, sim):
    """Bottom center - Race statistics"""
    panel_w = 600
    panel_h = 120
    panel_x = (SCREEN_W - panel_w) // 2
    panel_y = SCREEN_H - panel_h - 10
    
    pygame.draw.rect(surf, PANEL_BG, pygame.Rect(panel_x, panel_y, panel_w, panel_h), border_radius=8)
    pygame.draw.rect(surf, YELLOW, pygame.Rect(panel_x, panel_y, panel_w, panel_h), 2, border_radius=8)
    
    # Header
    surf.blit(font_lg.render("RACE STATISTICS", True, YELLOW), (panel_x + 15, panel_y + 10))
    
    y_pos = panel_y + 40
    
    # Calculate race statistics
    total_cars = len(sim.cars)
    finished_cars = len([c for c in sim.cars if c.finished])
    racing_cars = total_cars - finished_cars
    cars_in_pit = len([c for c in sim.cars if c.in_pit])
    
    avg_speed = sum(c.speed for c in sim.cars) / total_cars if total_cars > 0 else 0
    
    fastest_lap = None
    fastest_car = None
    for car in sim.cars:
        if car.best_lap is not None:
            if fastest_lap is None or car.best_lap < fastest_lap:
                fastest_lap = car.best_lap
                fastest_car = car
    
    # Display stats in columns
    col1_x = panel_x + 20
    col2_x = panel_x + 200
    col3_x = panel_x + 380
    
    surf.blit(font_sm.render(f"Cars Racing: {racing_cars}/{total_cars}", True, WHITE),
              (col1_x, y_pos))
    surf.blit(font_sm.render(f"Cars Finished: {finished_cars}", True, WHITE),
              (col2_x, y_pos))
    surf.blit(font_sm.render(f"Cars in Pit: {cars_in_pit}", True, ORANGE),
              (col3_x, y_pos))
    y_pos += 25
    
    surf.blit(font_sm.render(f"Avg Speed: {avg_speed*20:.1f} KPH", True, WHITE),
              (col1_x, y_pos))
    
    if fastest_lap and fastest_car:
        surf.blit(font_sm.render(f"Fastest Lap: {fastest_lap:.2f}s", True, GREEN),
                  (col2_x, y_pos))
        surf.blit(font_sm.render(f"By: {fastest_car.id}", True, fastest_car.color),
                  (col3_x, y_pos))
    
    y_pos += 25
    
    # Incidents and penalties
    total_penalties = sum(c.penalties for c in sim.cars)
    surf.blit(font_sm.render(f"Total Penalties: {total_penalties:.0f}s", True, RED if total_penalties > 0 else WHITE),
              (col1_x, y_pos))

def draw_minimap(surf, sim):
    """Bottom right - Track minimap"""
    map_w = 320
    map_h = 220
    map_x = SCREEN_W - map_w - 440
    map_y = SCREEN_H - map_h - 10
    
    pygame.draw.rect(surf, PANEL_BG, pygame.Rect(map_x, map_y, map_w, map_h), border_radius=8)
    pygame.draw.rect(surf, YELLOW, pygame.Rect(map_x, map_y, map_w, map_h), 2, border_radius=8)
    
    # Header
    surf.blit(font_md.render("TRACK MAP", True, YELLOW), (map_x + 10, map_y + 8))
    
    # Calculate scale to fit track
    padding = 30
    scale_x = (map_w - padding * 2) / WORLD_W
    scale_y = (map_h - padding * 2) / WORLD_H
    scale = min(scale_x, scale_y)
    
    offset_x = map_x + map_w // 2
    offset_y = map_y + map_h // 2 + 10
    
    # Draw track outline
    waypoints = sim.track.waypoints
    map_points = []
    for x, y in waypoints:
        sx = int((x - WORLD_W // 2) * scale * 2.5) + offset_x # Scale up minimap track
        sy = int((y - WORLD_H // 2) * scale * 2.5) + offset_y
        map_points.append((sx, sy))
        
    pygame.draw.lines(surf, GRAY, True, map_points, 3)
    
    # Draw start line
    sx, sy = sim.track.start_line
    start_x = int((sx - WORLD_W // 2) * scale * 2.5) + offset_x
    start_y = int((sy - WORLD_H // 2) * scale * 2.5) + offset_y
    pygame.draw.circle(surf, WHITE, (start_x, start_y), 5)
    
    # Draw cars
    for car in sim.cars:
        cx = int((car.x - WORLD_W // 2) * scale * 2.5) + offset_x
        cy = int((car.y - WORLD_H // 2) * scale * 2.5) + offset_y
        
        # Draw car position
        pygame.draw.circle(surf, car.color, (cx, cy), 4)
        
        # Draw position number for top 3
        if car.position <= 3:
            pos_text = font_xs.render(str(car.position), True, WHITE)
            surf.blit(pos_text, (cx + 6, cy - 4))

def get_player_action(keys):
    """Get keyboard input for player car"""
    throttle = 1.0 if (keys[pygame.K_w] or keys[pygame.K_UP]) else (-1.0 if (keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0.0)
    steer = -1.0 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else (1.0 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0.0)
    
    return {
        'throttle': throttle,
        'steer': steer,
        'pit': keys[pygame.K_SPACE],
        'use_ers': keys[pygame.K_e],
        'use_drs': keys[pygame.K_f]
    }

def main():
    sim = SimulationManager()
    
    running = True
    paused = False
    
    # Camera follows player car (P1)
    cam_x = sim.cars[0].x - (SCREEN_W // 2)
    cam_y = sim.cars[0].y - (SCREEN_H // 2)
    
    while running:
        dt = clock.tick(FPS) / 1000.0
        if dt > 0.05: dt = 0.05 # Prevent large physics steps if game lags
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_p:
                    paused = not paused
        
        if not paused:
            keys = pygame.key.get_pressed()
            player_action = get_player_action(keys)
            sim.step(dt, player_action)
        
        # Camera smoothing to follow the player car
        target_cam_x = sim.cars[0].x - ( (SCREEN_W - 850) / 2)
        target_cam_y = sim.cars[0].y - ( (SCREEN_H - 250) / 2)
        cam_x = lerp(cam_x, target_cam_x, 0.1)
        cam_y = lerp(cam_y, target_cam_y, 0.1)

        # Render
        screen.fill(DARK_BG)
        
        # Draw track and cars in center viewport
        viewport_x = 400
        viewport_y = 80
        viewport_w = SCREEN_W - 850
        viewport_h = SCREEN_H - 250
        
        # Create subsurface for track view
        track_surface = pygame.Surface((viewport_w, viewport_h))
        cam_offset = (int(cam_x), int(cam_y))
        sim.draw(track_surface, cam_offset)
        screen.blit(track_surface, (viewport_x, viewport_y))
        
        # Draw border around track view
        pygame.draw.rect(screen, YELLOW, pygame.Rect(viewport_x, viewport_y, viewport_w, viewport_h), 2)
        
        # Draw all UI panels
        draw_header(screen, sim)
        draw_leaderboard(screen, sim)
        draw_telemetry(screen, sim)
        draw_race_stats(screen, sim)
        draw_minimap(screen, sim)
        
        # Control instructions
        status_text = "PAUSED" if paused else "LIVE"
        status_color = ORANGE if paused else GREEN
        controls = f"[{status_text}] W/A/S/D: Drive | E: ERS | F: DRS | SPACE: Pit | P: Pause | ESC: Exit"
        screen.blit(font_sm.render(controls, True, status_color), (viewport_x + 10, viewport_y + viewport_h + 10))
        
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()