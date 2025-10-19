import pygame
import math
import os
from src.core.tracks import THEMES, TRACK_DATA

class Button:
    """A simple clickable button class."""
    def __init__(self, x, y, width, height, text, color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False

    def draw(self, screen, font):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        text_surf = font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def check_hover(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered

class Display:
    def __init__(self):
        pygame.init()
        self.width = 1280
        self.height = 900
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("F1 Grand Prix Simulation")
        
        # Fonts
        self.font_large = pygame.font.SysFont("helvetica", 72, bold=True)
        self.font_medium = pygame.font.SysFont("helvetica", 36)
        self.font_small = pygame.font.SysFont("monospace", 18)
        self.font_tiny = pygame.font.SysFont("monospace", 14)
        
        self.clock = pygame.time.Clock()
        self.track_data = None
        self.env = None
        self._load_car_images()

    def _load_car_images(self):
        self.car_images = []
        try:
            for i in range(1, 5):
                path = os.path.join("assets", f"car{i}.png")
                self.car_images.append(pygame.image.load(path).convert_alpha())
        except Exception as e:
            print(f"Could not load car images from 'assets' folder: {e}")
            # Create fallback colored surfaces
            colors = [(200,0,0), (0,0,200), (255,255,0), (0,200,0)]
            for color in colors:
                surf = pygame.Surface((40, 20), pygame.SRCALPHA)
                surf.fill(color)
                self.car_images.append(surf)

    def set_track(self, track_data, env):
        self.track_data = track_data
        self.env = env
        self.theme = track_data["theme"]
        self.track_path = track_data["path"]
        self._precalculate_path()

    def _precalculate_path(self):
        self.path_segments_len = []
        self.path_cumulative_len = [0]
        total_len = 0
        for i in range(len(self.track_path)):
            p1 = self.track_path[i]
            p2 = self.track_path[(i + 1) % len(self.track_path)]
            dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            self.path_segments_len.append(dist)
            total_len += dist
            self.path_cumulative_len.append(total_len)
        self.total_path_length = total_len

    def _get_point_on_path(self, progress):
        target_dist = progress * self.total_path_length
        segment_idx = next((i for i, total in enumerate(self.path_cumulative_len) if total > target_dist), len(self.path_cumulative_len) - 2)
        
        p1 = self.track_path[segment_idx]
        p2 = self.track_path[(segment_idx + 1) % len(self.track_path)]

        dist_into_segment = target_dist - self.path_cumulative_len[segment_idx]
        segment_len = self.path_segments_len[segment_idx]
        segment_progress = dist_into_segment / segment_len if segment_len > 0 else 0

        x = p1[0] + (p2[0] - p1[0]) * segment_progress
        y = p1[1] + (p2[1] - p1[1]) * segment_progress
        angle = math.degrees(math.atan2(-(p2[1] - p1[1]), p2[0] - p1[0]))
        return (x, y), angle

    # --- DRAWING METHODS FOR EACH GAME STATE ---

    def draw_main_menu(self, buttons):
        self.screen.fill((10, 10, 30))
        title_text = self.font_large.render("F1 Grand Prix", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(self.width / 2, self.height / 3))
        self.screen.blit(title_text, title_rect)
        for button in buttons.values():
            button.draw(self.screen, self.font_medium)
        pygame.display.flip()

    def draw_track_selection(self, buttons, tracks):
        self.screen.fill((10, 10, 30))
        title = self.font_medium.render("Select a Circuit", True, (255, 255, 255))
        self.screen.blit(title, (20, 20))
        for key, button in buttons.items():
            # Draw track preview
            preview_rect = pygame.Rect(button.rect.left, button.rect.top - 170, button.rect.width, 150)
            theme = THEMES[key]
            pygame.draw.rect(self.screen, theme["grass"], preview_rect)
            pygame.draw.rect(self.screen, theme["background"], preview_rect, 10)
            
            # Simple path scaling for preview
            path = TRACK_DATA[key]["path"]
            xs = [p[0] for p in path]
            ys = [p[1] for p in path]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
            scale = min(preview_rect.width * 0.8 / (max_x - min_x), preview_rect.height * 0.8 / (max_y - min_y))
            
            preview_path = [
                (preview_rect.centerx + (x - (min_x+max_x)/2) * scale,
                 preview_rect.centery + (y - (min_y+max_y)/2) * scale) for x, y in path
            ]
            pygame.draw.lines(self.screen, theme["track"], False, preview_path, 3)

            button.draw(self.screen, self.font_small)
        pygame.display.flip()

    def draw_race(self):
        # Environment
        self.screen.fill(self.theme["grass"])
        pygame.draw.rect(self.screen, self.theme["background"], (20, 20, self.width-40, self.height-40))
        pygame.draw.lines(self.screen, self.theme["rumble_strip"], True, self.track_path, width=50)
        pygame.draw.lines(self.screen, self.theme["track"], True, self.track_path, width=40)
        
        # Draw cars and HUD
        self._draw_cars()
        self._draw_race_hud()
        
        pygame.display.flip()
        self.clock.tick(60)

    def draw_race_end(self, button):
        s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (0, 0))

        title = self.font_large.render("Race Finished", True, (255, 255, 255))
        self.screen.blit(title, title.get_rect(centerx=self.width/2, y=100))
        
        sorted_cars = sorted(zip(self.env.cars, self.env.laps), key=lambda x:(x[1], x[0].pos), reverse=True)

        for rank, (car, lap) in enumerate(sorted_cars, start=1):
            text = f"{rank}. Car-{car.id} - Laps: {lap}"
            render_text = self.font_medium.render(text, True, (255, 255, 255))
            self.screen.blit(render_text, render_text.get_rect(centerx=self.width/2, y=250 + rank*50))
        
        button.draw(self.screen, self.font_medium)
        pygame.display.flip()


    # --- HELPER DRAWING METHODS ---
    
    def _draw_cars(self):
        lane_width = 10
        for car in self.env.cars:
            if car.done: continue
            progress = car.pos / self.env.track.length
            (x, y), angle = self._get_point_on_path(progress)
            
            # Dynamic scaling based on speed
            base_w, base_h = 40, 20
            speed_scale = 1 + (car.speed / 500) # Slightly larger at high speed
            w, h = int(base_w * speed_scale), int(base_h * speed_scale)
            
            scaled_img = pygame.transform.scale(self.car_images[car.id], (w, h))
            rotated_img = pygame.transform.rotate(scaled_img, angle)
            
            offset_angle_rad = math.radians(angle + 90)
            offset = (car.id - (len(self.env.cars) - 1) / 2) * lane_width
            offset_x = offset * math.cos(offset_angle_rad)
            offset_y = -offset * math.sin(offset_angle_rad)
            
            rect = rotated_img.get_rect(center=(x + offset_x, y + offset_y))
            self.screen.blit(rotated_img, rect.topleft)

    def _draw_race_hud(self):
        # Semi-transparent background for HUD
        hud_surf = pygame.Surface((self.width, 140), pygame.SRCALPHA)
        hud_surf.fill((0, 0, 0, 150))
        self.screen.blit(hud_surf, (0, 0))
        
        # Race Time
        minutes = int(self.env.race_time // 60)
        seconds = int(self.env.race_time % 60)
        time_text = f"TIME: {minutes:02d}:{seconds:02d}"
        time_surf = self.font_medium.render(time_text, True, (255, 255, 255))
        self.screen.blit(time_surf, (self.width - 250, 20))
        
        # Leaderboard
        sorted_cars = sorted(zip(self.env.cars, self.env.laps), key=lambda x:(x[1], x[0].pos), reverse=True)
        for rank, (car, lap) in enumerate(sorted_cars, start=1):
            text = (f"{rank}. C{car.id} | L:{lap}/{self.env.total_laps} | "
                    f"S:{car.speed:3.0f} | F:{car.fuel:3.0f} | "
                    f"T:{car.tyre_wear:.2f} | D:{car.damage:.2f}")
            color = self.theme.get("font", (255, 255, 255))
            render_text = self.font_tiny.render(text, True, color)
            self.screen.blit(render_text, (20, 10 + (rank * 25)))

    def close(self):
        pygame.quit()

