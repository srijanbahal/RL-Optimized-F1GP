
import math
import random
import pygame
from collections import deque
import Box2D  # Import the physics engine
from Box2D.b2 import world, polygonShape, dynamicBody, staticBody

# ---------- CONFIG ----------
pygame.init()
info = pygame.display.Info()
SCREEN_W, SCREEN_H = info.current_w, info.current_h
BASE_W, BASE_H = 1920, 1080

# Physics world scaling factor (Box2D works best with small numbers)
PPM = 20.0

WORLD_W, WORLD_H = 3000, 2000
FPS = 60
TIME_STEP = 1.0 / FPS

NUM_AI = 9
LAPS_TO_FINISH = 5

# Car physics (now used to apply forces)
ACCEL_FORCE = 180.0
BRAKE_FORCE = 220.0
TURN_TORQUE = 200.0  # This will be modulated by the smooth steering
DRAG = 0.992 # Kept for high-speed drag simulation

# Tire compounds
TIRE_COMPOUNDS = {
    'soft': {'grip': 1.25, 'color': (255, 50, 50)},
    'medium': {'grip': 1.0, 'color': (255, 200, 0)},
    'hard': {'grip': 0.85, 'color': (220, 220, 220)},
}

# Engine modes
ENGINE_MODES = {
    'qualifying': {'power': 1.15},
    'race': {'power': 1.0},
    'conservation': {'power': 0.8},
}

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_BG = (10, 12, 18)
PANEL_BG = (20, 25, 35)
HEADER_BG = (25, 30, 42)
GRAY = (120, 120, 120)
DARK_GRAY = (40, 45, 55)
GREEN = (46, 204, 113)
RED = (231, 76, 60)
YELLOW = (241, 196, 15)
ORANGE = (230, 126, 34)
LIGHT_GRAY = (189, 195, 199)
TRACK_GRAY = (149, 165, 166)
GRASS_GREEN = (118, 188, 74)
SAND_YELLOW = (230, 218, 158)
UI_BORDER = (60, 65, 75)


screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("F1 Race Control - Admin Panel")
clock = pygame.time.Clock()

# ========== DYNAMIC FONT AND UI SCALING ==========
def scale_x(val): return int(val * (SCREEN_W / BASE_W))
def scale_y(val): return int(val * (SCREEN_H / BASE_H))
def get_scaled_font_size(base_size):
    scale_factor = min(SCREEN_W / BASE_W, SCREEN_H / BASE_H)
    return max(10, int(base_size * scale_factor))

font_xs = pygame.font.SysFont("Consolas", get_scaled_font_size(12))
font_sm = pygame.font.SysFont("Consolas", get_scaled_font_size(14))
font_md = pygame.font.SysFont("Consolas", get_scaled_font_size(16))
font_lg = pygame.font.SysFont("Consolas", get_scaled_font_size(18), bold=True)
font_xl = pygame.font.SysFont("Consolas", get_scaled_font_size(22), bold=True)

def clamp(x, a, b): return max(a, min(b, x))
def lerp(a, b, t): return a + (b - a) * t

def catmull_rom_spline(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
    y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
    return x, y

# ---------- Track ----------
class Track:
    def __init__(self):
        """
        Redesigned F1-style circuit:
        - Start/finish straight in the center horizontally
        - Long flowing corners
        - Pit lane parallel to main straight
        """
        # Wider, longer F1-style layout (roughly "loop" with chicane)
        control_points = [
            (600, 1400), (1200, 1400), (1800, 1300), (2300, 1000), (2300, 600),
            (1800, 400), (1200, 400), (800, 600), (600, 900), (700, 1200)
        ]

        self.waypoints = []
        num_points = len(control_points)
        for i in range(num_points):
            p0, p1 = control_points[(i - 1 + num_points) % num_points], control_points[i]
            p2, p3 = control_points[(i + 1) % num_points], control_points[(i + 2) % num_points]
            for t_step in range(50):  # smoother curvature
                self.waypoints.append(catmull_rom_spline(p0, p1, p2, p3, t_step / 50.0))

        # Geometry parameters
        self.track_width, self.barrier_width = 240, 25

        # Start line near center, on main straight
        self.start_line = (1200, 1400)

        # Pit lane parallel to main straight
        self.pit_entry = (1200, 1500)
        self.pit_exit = (1800, 1500)
        self.pit_rect = pygame.Rect(1150, 1480, 750, 100)

    def draw(self, surf, cam_offset):
        surf.fill(GRASS_GREEN)
        pygame.draw.rect(surf, GRASS_GREEN, (0, 0, surf.get_width(), surf.get_height()))

        # Draw sand background (large to prevent leaks)
        track_points = [(p[0] - cam_offset[0], p[1] - cam_offset[1]) for p in self.waypoints]
        pygame.draw.lines(surf, SAND_YELLOW, True, track_points, self.track_width + 180)

        # Draw main asphalt track
        pygame.draw.lines(surf, TRACK_GRAY, True, track_points, self.track_width + 20)

        # Barriers
        for i, p1 in enumerate(track_points):
            p2 = track_points[(i + 1) % len(track_points)]
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            mag = math.hypot(dx, dy)
            if mag == 0:
                continue
            nx, ny = -dy / mag, dx / mag
            offset = self.track_width / 2 + self.barrier_width / 2

            p1_outer = (p1[0] + nx * offset, p1[1] + ny * offset)
            p2_outer = (p2[0] + nx * offset, p2[1] + ny * offset)
            p1_inner = (p1[0] - nx * offset, p1[1] - ny * offset)
            p2_inner = (p2[0] - nx * offset, p2[1] - ny * offset)

            color = RED if (i % 16 < 8) else WHITE
            pygame.draw.line(surf, color, p1_outer, p2_outer, self.barrier_width)
            pygame.draw.line(surf, color, p1_inner, p2_inner, self.barrier_width)

        # Draw pit lane
        pit_rect = self.pit_rect.move(-cam_offset[0], -cam_offset[1])
        pygame.draw.rect(surf, (50, 50, 65), pit_rect)
        pygame.draw.rect(surf, WHITE, pit_rect, 2)
        pit_text = font_sm.render("PIT LANE", True, YELLOW)
        surf.blit(pit_text, (pit_rect.x + 10, pit_rect.y + 10))

        # Draw start line
        sx, sy = self.start_line
        for i in range(-3, 4):
            for j in range(10):
                pygame.draw.rect(
                    surf,
                    BLACK if (i + j) % 2 == 0 else WHITE,
                    (sx - cam_offset[0] + i * 15 - 50,
                     sy - cam_offset[1] + j * 10 - 50, 14, 10)
                )

        # Centerline dots
        for i in range(0, len(self.waypoints), 20):
            x, y = self.waypoints[i]
            pygame.draw.circle(surf, WHITE, (int(x - cam_offset[0]), int(y - cam_offset[1])), 3)



# ---------- Car ----------
class Car:
    def __init__(self, sim_world, id, x, y, color, team_name):
        # Telemetry-related properties
        self.fuel = 100.0          # percentage
        self.tire_wear = 0.0       # percentage
        self.tire_temp = 45.0      # °C
        self.brake_temp = 40.0     # °C
        self.engine_temp = 85.0    # °C
        self.ers = 100.0           # %
        self.downforce_level = 5
        self.drs_enabled = False

        self.id, self.team_name, self.color = id, team_name, color
        self.width, self.length = 20, 36
        
        # ========== PyBox2D BODY CREATION ==========
        self.body = sim_world.CreateDynamicBody(
            position=(x / PPM, y / PPM),
            angle=0,
            linearDamping=0.8,   # Simulates friction and air resistance
            angularDamping=4.0, # Makes turning more stable
        )
        self.body.userData = self # Link the body back to the car object
        shape = polygonShape(box=(self.length / 2 / PPM, self.width / 2 / PPM))
        self.body.CreateFixture(shape=shape, density=1.0)
        # ==========================================
        
        # Public properties read from physics body
        self.x, self.y, self.angle, self.speed = x, y, 0, 0

        self.lap, self.finished, self.position = 0, False, 1
        self.total_time, self.current_lap_time, self.best_lap, self.last_lap_time = 0.0, 0.0, None, None
        
        self.tire_compound = random.choice(['soft', 'medium', 'hard'])
        self.engine_mode = 'race'
        self.in_pit, self.pit_stops = False, 0
        self.waypoint_index = 0
        self._last_pass = None

    def get_lateral_velocity(self):
        """Returns the sideways velocity vector."""
        right_normal = self.body.GetWorldVector((0, 1))
        return right_normal.dot(self.body.linearVelocity) * right_normal

    def update_physics(self, action):
        """
        Apply forces and torques to this car's physics body based on control actions.
        Realistic and stable F1-style vehicle dynamics tuned for Box2D.
        """
        # ---------------------------------------------------
        # CONFIGURABLE PARAMETERS (tune these as needed)
        # ---------------------------------------------------
        grip = TIRE_COMPOUNDS[self.tire_compound]['grip']
        engine_power = ENGINE_MODES[self.engine_mode]['power']
        max_accel_force = ACCEL_FORCE * engine_power
        max_brake_force = BRAKE_FORCE
        max_turn_torque = TURN_TORQUE
        lateral_grip_factor = 8.0 * grip      # higher = more grip, less sliding
        longitudinal_drag_coeff = 0.25        # 0.2–0.3 is realistic
        angular_vel_limit = 10.0              # clamp spin speed (rad/s)
        angular_vel_damp_factor = 0.9         # damping multiplier when limit exceeded
        steer_speed_scale_min = 0.5           # stronger steering at low speed
        steer_speed_scale_max = 10.0          # weaker steering at high speed
        throttle_smooth = 0.2                 # 0.1 = sluggish, 0.3 = twitchy
        # ---------------------------------------------------

        # --- Smoothed throttle for stability ---
        throttle_cmd = clamp(action.get('throttle', 0.0), -1.0, 1.0)
        self.throttle_input = getattr(self, 'throttle_input', 0.0)
        self.throttle_input = lerp(self.throttle_input, throttle_cmd, throttle_smooth)

        steer_input = clamp(action.get('steer', 0.0), -1.0, 1.0)

        # --- Get orientation vectors ---
        forward_normal = self.body.GetWorldVector(localVector=(1, 0))
        right_normal   = self.body.GetWorldVector(localVector=(0, 1))
        vel = self.body.linearVelocity

        # ===================================================
        # 1️⃣  LATERAL FRICTION  (kill side slip)
        # ===================================================
        lateral_speed = right_normal.dot(vel)
        lateral_impulse = -right_normal * clamp(
            lateral_speed * self.body.mass,
            -self.body.mass * lateral_grip_factor,
            self.body.mass * lateral_grip_factor,
        )
        self.body.ApplyLinearImpulse(lateral_impulse, self.body.worldCenter, True)

        # ===================================================
        # 2️⃣  LONGITUDINAL DRAG (air resistance)
        # ===================================================
        forward_speed = forward_normal.dot(vel)
        drag_force = -forward_normal * forward_speed * abs(forward_speed) * longitudinal_drag_coeff
        self.body.ApplyForce(drag_force, self.body.worldCenter, True)

        # ===================================================
        # 3️⃣  ACCELERATION / BRAKING
        # ===================================================
        if self.throttle_input > 0.0:
            # accelerate
            accel_force = forward_normal * max_accel_force * self.throttle_input
            self.body.ApplyForce(accel_force, self.body.worldCenter, True)
        elif self.throttle_input < 0.0:
            # braking
            brake_force = forward_normal * max_brake_force * self.throttle_input
            self.body.ApplyForce(brake_force, self.body.worldCenter, True)

        # ===================================================
        # 4️⃣  STEERING TORQUE (speed-scaled)
        # ===================================================
        speed = max(self.body.linearVelocity.length, steer_speed_scale_min)
        speed_factor = clamp(speed, steer_speed_scale_min, steer_speed_scale_max)
        turn_strength = max_turn_torque * steer_input / speed_factor
        self.body.ApplyTorque(turn_strength, True)

        # ===================================================
        # 5️⃣  STABILIZATION (spin and velocity clamping)
        # ===================================================
        if abs(self.body.angularVelocity) > angular_vel_limit:
            self.body.angularVelocity *= angular_vel_damp_factor

        # --- optional tiny linear damping correction ---
        if vel.length > 0.001:
            self.body.linearDamping = 0.3 + 0.1 * (1.0 - grip)
        else:
            self.body.linearDamping = 1.0

        
    def check_pit_stop(self):
        """Simulated pit stop entry, stay, and exit."""
        # Start pit stop if fuel/tire thresholds crossed and not already in pit
        if not self.in_pit and (self.fuel < 15.0 or self.tire_wear > 80.0):
            # Drive toward pit lane
            self.target_pit = (random.uniform(1850, 2100), random.uniform(1520, 1580))
            self.in_pit = True
            self.pit_timer = 0.0
            self.pit_stops += 1

        # If in pit lane, simulate being stationary for a while
        if self.in_pit:
            self.pit_timer += 1 / FPS

            # During first 1s: move slowly into pit lane area
            if self.pit_timer < 1.0:
                tx, ty = self.target_pit
                dx, dy = tx - self.x, ty - self.y
                angle = math.atan2(dy, dx)
                self.body.linearVelocity = (math.cos(angle) * 2.0 / PPM, math.sin(angle) * 2.0 / PPM)

            # Stay still during service
            elif 1.0 <= self.pit_timer < 4.0:
                self.body.linearVelocity = (0, 0)

            # Exit pit after 4s
            else:
                self.in_pit = False
                self.target_pit = None
                self.fuel = 100.0
                self.tire_wear = 0.0
                self.tire_temp = 45.0
                self.brake_temp = 40.0
                self.engine_temp = 85.0
                self.ers = 100.0




    def sync_with_physics(self):
        """Updates car's state from its physics body."""
        pos = self.body.position
        self.x, self.y = pos.x * PPM, pos.y * PPM
        self.angle = math.degrees(self.body.angle)
        self.speed = self.body.linearVelocity.length * PPM
        # Simple telemetry simulation
        self.fuel = max(0.0, self.fuel - 0.01)                 # burns fuel slowly
        self.tire_wear = min(100.0, self.tire_wear + 0.005)    # tires wear over time
        self.tire_temp = min(130.0, self.tire_temp + abs(self.speed) * 0.002)
        self.brake_temp = min(1000.0, self.brake_temp + abs(self.speed) * 0.005)
        self.engine_temp = clamp(85.0 + abs(self.speed) * 0.02, 85.0, 130.0)
        self.ers = max(0.0, self.ers - 0.002)
        self.check_pit_stop()



    def draw(self, surf, cam_offset):
        car_surf = pygame.Surface((self.length, self.width), pygame.SRCALPHA)
        pygame.draw.rect(car_surf, self.color, (0, 0, self.length, self.width), border_radius=4)
        pygame.draw.rect(car_surf, (30, 30, 30), (self.length * 0.4, 4, self.length * 0.25, self.width - 8), border_radius=2)
        tire_color = TIRE_COMPOUNDS[self.tire_compound]['color']
        pygame.draw.circle(car_surf, tire_color, (self.length - 8, 4), 3)
        pygame.draw.circle(car_surf, tire_color, (self.length - 8, self.width - 4), 3)
        
        rotated = pygame.transform.rotate(car_surf, -self.angle)
        rect = rotated.get_rect(center=(self.x - cam_offset[0], self.y - cam_offset[1]))
        surf.blit(rotated, rect.topleft)
    

# ---------- AI Controller ----------
class AIController:
    def __init__(self, car, waypoints):
        self.car, self.waypoints, self.idx = car, waypoints, 0

    def step(self):
        tx, ty = self.waypoints[self.idx]
        if math.hypot(tx - self.car.x, ty - self.car.y) < 120:
            self.idx = (self.idx + 1) % len(self.waypoints)
        
        self.car.waypoint_index = self.idx
        desired = math.degrees(math.atan2(ty - self.car.y, tx - self.car.x))
        diff = (desired - self.car.angle + 540) % 360 - 180
        
        return {'throttle': 0.8, 'steer': clamp(diff / 45.0, -1.0, 1.0)}

# ---------- Simulation ----------
class SimulationManager:
    def __init__(self):
        self.world = world(gravity=(0, 0))
        self.track = Track()

        # Only 6 teams (simpler grid)
        teams = [
            ("Red Bull", (30, 65, 174)),
            ("Ferrari", (220, 0, 0)),
            ("Mercedes", (0, 210, 190)),
            ("McLaren", (255, 135, 0)),
            ("Aston Martin", (0, 111, 98)),
            ("Alpine", (34, 147, 209))
        ]

        self.cars = []
        sx, sy = self.track.start_line

        # Create only AI cars now
        for i in range(len(teams)):
            team_name, color = teams[i]
            offset_x, offset_y = -(i // 2) * 60, ((i % 2) - 0.5) * 45
            car_id = f"AI{i+1}"
            self.cars.append(Car(self.world, car_id, sx + offset_x, sy + offset_y, color, team_name))

        # Default focus = first car (Red Bull)
        self.focused_car = self.cars[0]

        # AI Controllers for all cars
        self.ai_ctrl = [AIController(c, self.track.waypoints) for c in self.cars]

        self.time, self.race_started, self.start_countdown = 0.0, False, 5.0

    def set_focus_car(self, car):
        """Set which car the camera should follow."""
        if car in self.cars:
            self.focused_car = car
    
    def step(self, dt, player_action):
        if not self.race_started:
            self.start_countdown -= dt
            if self.start_countdown <= 0: self.race_started = True
            else: return

        # Update physics based on actions
        # Update all AI cars
        for ctrl in self.ai_ctrl:
            ctrl.car.update_physics(ctrl.step())
            
        # Step the physics world
        self.world.Step(TIME_STEP, 10, 8)
        
        # Sync game objects with physics bodies
        for car in self.cars:
            car.sync_with_physics()
            car.total_time += dt
            car.current_lap_time += dt

        # Lap detection and positioning
        self.update_race_progress()
        self.time += dt
    def update_race_progress(self):
        for car in self.cars:
            if car.finished:
                continue

            sx, sy = self.track.start_line
            # detect crossing start line
            if math.hypot(car.x - sx, car.y - sy) < 100 and (
                car._last_pass is None or self.time - car._last_pass > 10.0
            ):
                car._last_pass = self.time
                if car.lap > 0:
                    car.last_lap_time = car.current_lap_time
                    if car.best_lap is None or car.current_lap_time < car.best_lap:
                        car.best_lap = car.current_lap_time
                    car.current_lap_time = 0.0
                car.lap += 1

                if car.lap > LAPS_TO_FINISH:
                    car.finished = True
                    car.body.linearVelocity = (0, 0)
                    car.body.angularVelocity = 0

        # Sort leaderboard
        leaderboard = self.get_leaderboard()
        for i, car in enumerate(leaderboard):
            car.position = i + 1

        # Stop all cars when everyone finishes
        if all(c.finished for c in self.cars):
            for c in self.cars:
                c.body.linearVelocity = (0, 0)
                c.body.angularVelocity = 0


    def get_leaderboard(self):
        def race_key(c): return (-c.lap, -(c.waypoint_index / len(self.track.waypoints)))
        racing = sorted([c for c in self.cars if not c.finished], key=race_key)
        finished = sorted([c for c in self.cars if c.finished], key=lambda c: c.total_time)
        return finished + racing

    def draw(self, surf, cam_offset):
        self.track.draw(surf, cam_offset)
        for car in sorted(self.cars, key=lambda c: c.y):
            car.draw(surf, cam_offset)

# ========== UI DRAWING FUNCTIONS (IMPROVED) ==========
def draw_panel(surf, rect, title):
    pygame.draw.rect(surf, PANEL_BG, rect, border_radius=8)
    pygame.draw.rect(surf, UI_BORDER, rect, 2, border_radius=8)
    header_rect = (rect.x, rect.y, rect.width, scale_y(40))
    pygame.draw.rect(surf, HEADER_BG, header_rect, border_top_left_radius=8, border_top_right_radius=8)
    pygame.draw.line(surf, UI_BORDER, (rect.x, rect.y + scale_y(40)), (rect.x + rect.width, rect.y + scale_y(40)), 2)
    title_surf = font_lg.render(title, True, YELLOW)
    surf.blit(title_surf, (rect.x + 15, rect.y + 8))

def draw_header(surf, sim):
    header_rect = pygame.Rect(0, 0, SCREEN_W, scale_y(70))
    pygame.draw.rect(surf, HEADER_BG, header_rect)
    pygame.draw.line(surf, YELLOW, (0, header_rect.h), (SCREEN_W, header_rect.h), 3)
    
    title = font_xl.render(f"F1 RACE CONTROL", True, YELLOW)
    surf.blit(title, (scale_x(20), scale_y(15)))
    
    info_text = f"Race Time: {sim.time:.1f}s   Laps: {LAPS_TO_FINISH}   Weather: Clear | Track: 35.0°C"
    surf.blit(font_md.render(info_text, True, LIGHT_GRAY), (scale_x(400), scale_y(25)))
    
    if not sim.race_started:
        text = font_xl.render(f"RACE STARTS IN: {max(0, sim.start_countdown):.1f}", True, RED)
        surf.blit(text, (SCREEN_W - text.get_width() - scale_x(30), scale_y(20)))


def draw_leaderboard(surf, sim):
    rect = pygame.Rect(scale_x(10), scale_y(80), scale_x(380), SCREEN_H - scale_y(90))
    draw_panel(surf, rect, "LIVE STANDINGS")
    
    mouse_pos = pygame.mouse.get_pos()
    mouse_clicked = pygame.mouse.get_pressed()[0]
    y_pos = rect.y + scale_y(55)
    clicked_car = None

    for i, car in enumerate(sim.get_leaderboard()):
        if y_pos > rect.y + rect.h - scale_y(40):
            break

        row_rect = pygame.Rect(rect.x + 10, y_pos, rect.width - 20, scale_y(35))
        is_hovered = row_rect.collidepoint(mouse_pos)
        is_focused = (car == sim.focused_car)

        # Background highlight (hover or selected)
        if is_focused:
            pygame.draw.rect(surf, (60, 60, 90), row_rect, border_radius=6)
        elif is_hovered:
            pygame.draw.rect(surf, (40, 40, 60), row_rect, border_radius=6)

        # Position badge
        pos_color = YELLOW if i == 0 else ORANGE if i == 1 else (200, 140, 30) if i == 2 else DARK_GRAY
        pygame.draw.rect(surf, pos_color, (rect.x + 15, y_pos + scale_y(5), scale_x(25), scale_y(25)), border_radius=4)
        pos_text = font_md.render(str(i + 1), True, BLACK if i < 3 else WHITE)
        surf.blit(pos_text, pos_text.get_rect(center=(rect.x + 28, y_pos + scale_y(17))))

        # Team color stripe
        pygame.draw.rect(surf, car.color, (rect.x + 50, y_pos + scale_y(5), 5, scale_y(25)))

        # Car & team text
        surf.blit(font_md.render(f"{car.id} - {car.team_name}", True, LIGHT_GRAY), (rect.x + 65, y_pos + scale_y(8)))

        # Status text
        status_text, status_color = (
            ("PIT", YELLOW) if car.in_pit
            else (("FIN", GREEN) if car.finished else (f"Lap {car.lap}/{LAPS_TO_FINISH}", GRAY))
        )
        surf.blit(font_sm.render(status_text, True, status_color), (rect.right - scale_x(90), y_pos + scale_y(10)))

        # Detect click
        if is_hovered and mouse_clicked:
            clicked_car = car

        y_pos += scale_y(38)

    # Update camera focus if a new car was clicked
    if clicked_car:
        sim.set_focus_car(clicked_car)
        
        
def draw_telemetry(surf, sim):
    rect = pygame.Rect(SCREEN_W - scale_x(430), scale_y(80), scale_x(420), SCREEN_H - scale_y(90))
    draw_panel(surf, rect, "CAR TELEMETRY")

    car = sim.focused_car if sim.focused_car else None
    if not car:
        return

    y_pos = rect.y + scale_y(55)

    def draw_row(label, value, color=LIGHT_GRAY):
        nonlocal y_pos
        surf.blit(font_md.render(f"{label}:", True, GRAY), (rect.x + 15, y_pos))
        surf.blit(font_md.render(str(value), True, color), (rect.x + scale_x(160), y_pos))
        y_pos += scale_y(30)

    def draw_bar(label, val, max_val, color):
        nonlocal y_pos
        progress = clamp(val / max_val, 0, 1)
        bar_w, bar_h = rect.width - 30, scale_y(22)
        pygame.draw.rect(surf, DARK_GRAY, (rect.x + 15, y_pos, bar_w, bar_h), border_radius=4)
        pygame.draw.rect(surf, color, (rect.x + 15, y_pos, bar_w * progress, bar_h), border_radius=4)
        txt = f"{label}: {val:.1f}" if isinstance(val, float) else f"{label}: {val*100:.0f}%"
        surf.blit(font_sm.render(txt, True, WHITE), (rect.x + 25, y_pos + 4))
        y_pos += scale_y(35)

    # ─── CORE INFO ───────────────────────────────
    draw_row("Car", f"{car.id} - {car.team_name}", car.color)
    draw_row("Position", f"{car.position} / {len(sim.cars)}")
    draw_row("Lap", f"{car.lap}/{LAPS_TO_FINISH}")
    y_pos += scale_y(10)

    # ─── SPEED / THROTTLE ────────────────────────
    draw_bar("Speed (KPH)", car.speed * 3.6, 350, GREEN)
    draw_bar("Throttle", abs(getattr(car, 'throttle_input', 0)) * 100, 100, ORANGE)
    y_pos += scale_y(10)

    # ─── TIRES ───────────────────────────────────
    draw_row("Compound", car.tire_compound.upper(), TIRE_COMPOUNDS[car.tire_compound]['color'])
    draw_bar("Wear", getattr(car, "tire_wear", 0.0), 100, YELLOW)
    draw_bar("Temp (°C)", getattr(car, "tire_temp", 45.0), 130, RED)
    y_pos += scale_y(10)

    # ─── FUEL & POWER ────────────────────────────
    draw_bar("Fuel (%)", getattr(car, "fuel", 100.0), 100, (80, 160, 255))
    draw_row("Engine Mode", car.engine_mode.upper(), LIGHT_GRAY)
    draw_bar("ERS (%)", getattr(car, "ers", 100.0), 100, GREEN)
    y_pos += scale_y(10)

    # ─── TEMPERATURES ────────────────────────────
    draw_bar("Brakes (°C)", getattr(car, "brake_temp", 40.0), 1000, ORANGE)
    draw_bar("Engine (°C)", getattr(car, "engine_temp", 85.0), 130, RED)
    y_pos += scale_y(10)

    # ─── LAP TIMES ───────────────────────────────
    draw_row("Current Lap", f"{car.current_lap_time:.2f}s")
    draw_row("Total Time", f"{car.total_time:.2f}s")
    y_pos += scale_y(10)

    # ─── AERODYNAMICS ────────────────────────────
    drs_status = getattr(car, "drs_enabled", False)
    draw_row("DRS", "ENABLED" if drs_status else "DISABLED", GREEN if drs_status else RED)
    draw_row("Downforce", f"{getattr(car, 'downforce_level', 5)}/10")
    draw_row("Pit Stops", getattr(car, "pit_stops", 0))


def draw_bottom_panels(surf, sim):
    stats_w, map_w = scale_x(500), scale_x(320)
    panel_h = scale_y(120)
    panel_y = SCREEN_H - panel_h - scale_y(10)
    
    # Race Stats
    stats_rect = pygame.Rect((SCREEN_W - stats_w - map_w - scale_x(10)) / 2, panel_y, stats_w, panel_h)
    draw_panel(surf, stats_rect, "RACE STATISTICS")
    
    # Minimap
    map_rect = pygame.Rect(stats_rect.right + scale_x(10), panel_y, map_w, panel_h)
    draw_panel(surf, map_rect, "TRACK MAP")
    
    # *** CHANGED: Use a dynamic scale based on track bounds ***
    min_x = min(p[0] for p in sim.track.waypoints)
    max_x = max(p[0] for p in sim.track.waypoints)
    min_y = min(p[1] for p in sim.track.waypoints)
    max_y = max(p[1] for p in sim.track.waypoints)
    track_world_w = max_x - min_x
    track_world_h = max_y - min_y
    track_center_x = (min_x + max_x) / 2
    track_center_y = (min_y + max_y) / 2
    
    scale = min((map_rect.w - 40) / track_world_w, (map_rect.h - 60) / track_world_h)
    offset_x, offset_y = map_rect.centerx, map_rect.centery + scale_y(10)
    
    map_points = [(((p[0] - track_center_x) * scale + offset_x), 
                   ((p[1] - track_center_y) * scale + offset_y)) 
                  for p in sim.track.waypoints]
    
    pygame.draw.lines(surf, GRAY, True, map_points, 3)
    
    for car in sim.cars:
        cx, cy = (car.x - track_center_x) * scale + offset_x, (car.y - track_center_y) * scale + offset_y
        pygame.draw.circle(surf, car.color, (cx, cy), 4)

# *** CHANGED: Modified function to smooth steering ***
def get_player_action(keys, old_steer):
    """
    Gets player input and returns a smoothed steering value.
    Returns: (action_dict, new_steer_value)
    """
    throttle = 1.0 if keys[pygame.K_w] else -1.0 if keys[pygame.K_s] else 0.0
    
    # Get target steer (full left, full right, or center)
    target_steer = -1.0 if keys[pygame.K_a] else 1.0 if keys[pygame.K_d] else 0.0
    
    # Smoothly move from the old steer value to the target
    # A lerp factor of 0.15 gives a responsive but smooth feel
    new_steer = lerp(old_steer, target_steer, 0.15)
    
    action = {
        'throttle': throttle,
        'steer': new_steer,
    }
    return action, new_steer

def main():
    sim = SimulationManager()
    running, paused = True, False
    # cam_x, cam_y = sim.cars[0].x - (SCREEN_W / 2), sim.cars[0].y - (SCREEN_H / 2)
    cam_x, cam_y = sim.focused_car.x - (SCREEN_W / 2), sim.focused_car.y - (SCREEN_H / 2)

    
    # *** CHANGED: Added current_steer variable ***
    current_steer = 0.0
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p: paused = not paused
        
        if not paused:
            # *** CHANGED: Update steering and get action dict ***
            player_action, current_steer = get_player_action(pygame.key.get_pressed(), current_steer)
            sim.step(TIME_STEP, player_action)
        
        # Viewport and Camera
        vp_x, vp_y = scale_x(400), scale_y(80)
        vp_w, vp_h = SCREEN_W - scale_x(850), SCREEN_H - scale_y(230)
        focus = sim.focused_car if sim.focused_car else sim.cars[0]
        target_cam_x, target_cam_y = focus.x - (vp_w / 2), focus.y - (vp_h / 2)
        cam_x, cam_y = lerp(cam_x, target_cam_x, 0.1), lerp(cam_y, target_cam_y, 0.1)

        
        # Drawing
        screen.fill(DARK_BG)
        # track_surface = pygame.Surface((vp_w, vp_h))
        track_surface = pygame.Surface((vp_w + 400, vp_h + 400))  # extra margin
        sim.draw(track_surface, (cam_x, cam_y))
        screen.blit(track_surface, (vp_x, vp_y))
        pygame.draw.rect(screen, UI_BORDER, (vp_x, vp_y, vp_w, vp_h), 2)
        
        draw_header(screen, sim)
        draw_leaderboard(screen, sim)
        draw_telemetry(screen, sim)
        draw_bottom_panels(screen, sim)
        
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()

if __name__ == "__main__":
    main()