import pygame
import random
import sys
from src.env.race_env import RaceEnvironment
from src.ui.display import Display, Button
from src.core.tracks import get_track

class Game:
    def __init__(self):
        self.ui = Display()
        self.game_state = "main_menu"
        self.env = None
        self.selected_track_key = None
        self.setup_buttons()

    def setup_buttons(self):
        """Initializes all clickable buttons for the UI."""
        self.buttons = {
            # Main Menu
            "start": Button(self.ui.width/2 - 150, 450, 300, 80, "START RACE", (200, 0, 0), (250, 50, 50)),
            "quit": Button(self.ui.width/2 - 150, 550, 300, 80, "QUIT", (80, 80, 80), (120, 120, 120)),
            
            # Track Selection (positions are placeholders, set dynamically)
            "desert": Button(100, 400, 250, 50, "Desert Circuit", (189, 164, 122), (218, 193, 153)),
            "forest": Button(400, 400, 250, 50, "Forest Circuit", (0, 100, 0), (34, 139, 34)),
            "alpine": Button(700, 400, 250, 50, "Alpine Circuit", (144, 238, 144), (174, 255, 174)),
            "night": Button(1000, 400, 250, 50, "Night Circuit", (15, 15, 40), (30, 30, 60)),

            # Race End
            "main_menu": Button(self.ui.width/2 - 150, 600, 300, 80, "MAIN MENU", (80, 80, 80), (120, 120, 120)),
        }
        
        # Dynamically position track buttons
        track_keys = ["desert", "forest", "alpine", "night"]
        total_width = len(track_keys) * 270 - 20
        start_x = self.ui.width/2 - total_width/2
        for i, key in enumerate(track_keys):
            self.buttons[key].rect.x = start_x + i * 280
            self.buttons[key].rect.y = self.ui.height / 2

    def run(self):
        """Main game loop."""
        while True:
            if self.game_state == "main_menu":
                self.main_menu_loop()
            elif self.game_state == "track_selection":
                self.track_selection_loop()
            elif self.game_state == "racing":
                self.racing_loop()
            elif self.game_state == "race_end":
                self.race_end_loop()

    def main_menu_loop(self):
        while self.game_state == "main_menu":
            mouse_pos = pygame.mouse.get_pos()
            
            # Update buttons
            self.buttons["start"].check_hover(mouse_pos)
            self.buttons["quit"].check_hover(mouse_pos)
            
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                if self.buttons["start"].is_clicked(event):
                    self.game_state = "track_selection"
                if self.buttons["quit"].is_clicked(event):
                    self.quit_game()

            # Drawing
            self.ui.draw_main_menu({"start": self.buttons["start"], "quit": self.buttons["quit"]})

    def track_selection_loop(self):
        track_buttons = {k: self.buttons[k] for k in ["desert", "forest", "alpine", "night"]}
        while self.game_state == "track_selection":
            mouse_pos = pygame.mouse.get_pos()
            for button in track_buttons.values():
                button.check_hover(mouse_pos)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                for key, button in track_buttons.items():
                    if button.is_clicked(event):
                        self.start_race(key)
                        return # Exit loop immediately

            self.ui.draw_track_selection(track_buttons, ["desert", "forest", "alpine", "night"])

    def start_race(self, track_key):
        self.selected_track_key = track_key
        track_data = get_track(track_key)
        self.env = RaceEnvironment(track=track_data["physics"], n=4, laps=3)
        self.ui.set_track(track_data, self.env)
        self.game_state = "racing"

    def racing_loop(self):
        if self.env.finished():
            self.game_state = "race_end"
            return
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit_game()
        
        # Your simulation logic
        acts = [random.uniform(-1, 1) for _ in self.env.cars]
        self.env.step(acts)
        self.ui.draw_race()

    def race_end_loop(self):
        while self.game_state == "race_end":
            mouse_pos = pygame.mouse.get_pos()
            self.buttons["main_menu"].check_hover(mouse_pos)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                if self.buttons["main_menu"].is_clicked(event):
                    self.game_state = "main_menu"
                    return # Exit loop
            
            self.ui.draw_race_end(self.buttons["main_menu"])

    def quit_game(self):
        self.ui.close()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
