from src.env.track import Track, TrackSection

# Each theme dictionary defines the colors for a specific track environment.
THEMES = {
    "desert": {
        "name": "Bahrain International Circuit",
        "background": (218, 193, 153), # Sandy beige
        "track": (80, 80, 80),
        "rumble_strip": (200, 0, 0),
        "grass": (189, 164, 122), # Darker sand
        "font": (0, 0, 0),
    },
    "forest": {
        "name": "Circuit de Spa-Francorchamps",
        "background": (34, 139, 34), # Forest green
        "track": (60, 60, 60),
        "rumble_strip": (255, 255, 0),
        "grass": (0, 100, 0), # Dark green
        "font": (255, 255, 255),
    },
    "alpine": {
        "name": "Red Bull Ring",
        "background": (240, 248, 255), # Alice blue for sky
        "track": (70, 70, 70),
        "rumble_strip": (0, 0, 200),
        "grass": (144, 238, 144), # Light green
        "font": (0, 0, 0),
    },
    "night": {
        "name": "Marina Bay Street Circuit",
        "background": (10, 10, 30), # Night sky blue
        "track": (50, 50, 50),
        "rumble_strip": (255, 255, 255),
        "grass": (15, 15, 40), # Darker blue
        "font": (255, 255, 255),
    }
}

# Track data is now defined using a path of (x, y) coordinates for drawing.
# The `sections` attribute for physics simulation can be derived or simplified.
TRACK_DATA = {
    "desert": {
        "path": [(1150, 750), (300, 750), (180, 680), (180, 500), (250, 430), (400, 480), (500, 420), (550, 280), (500, 200), (950, 200), (1050, 250), (1120, 350), (1120, 500), (1050, 600), (1000, 680)],
        "sections": [
            TrackSection("straight", 850, drs=True), TrackSection("corner", 200, radius=90), TrackSection("corner", 200, radius=90), TrackSection("straight", 200), TrackSection("corner", 150, radius=60), TrackSection("corner", 200, radius=80), TrackSection("corner", 300, radius=100), TrackSection("straight", 450), TrackSection("corner", 300, radius=70), TrackSection("straight", 500), TrackSection("corner", 400, radius=120), TrackSection("straight", 600, drs=True)
        ]
    },
    "forest": {
        "path": [(200, 450), (500, 200), (800, 200), (1050, 450), (1050, 650), (800, 800), (400, 800), (200, 650)],
         "sections": [
            TrackSection("corner", 400, radius=150), TrackSection("straight", 300), TrackSection("corner", 400, radius=150), TrackSection("straight", 200), TrackSection("corner", 300, radius=100), TrackSection("straight", 400, drs=True), TrackSection("corner", 300, radius=100), TrackSection("straight", 200, drs=True)
        ]
    },
    "alpine": {
        "path": [(300, 700), (1000, 700), (1100, 600), (1100, 300), (1000, 200), (400, 200), (300, 300), (450, 450), (300, 550)],
        "sections": [
            TrackSection("straight", 700, drs=True), TrackSection("corner", 200, radius=90), TrackSection("straight", 300), TrackSection("corner", 200, radius=90), TrackSection("straight", 600, drs=True), TrackSection("corner", 200, radius=80), TrackSection("corner", 200, radius=70), TrackSection("corner", 200, radius=90), TrackSection("straight", 150)
        ]
    },
    "night": {
        "path": [(250, 250), (1050, 250), (1050, 450), (850, 450), (850, 650), (1050, 650), (1050, 750), (250, 750), (250, 550), (450, 550), (450, 350), (250, 350)],
        "sections": [
            TrackSection("straight", 800, drs=True), TrackSection("corner", 100, radius=50), TrackSection("straight", 200), TrackSection("corner", 100, radius=50), TrackSection("straight", 200), TrackSection("corner", 100, radius=50), TrackSection("straight", 200), TrackSection("corner", 100, radius=50), TrackSection("straight", 800, drs=True), TrackSection("corner", 100, radius=50), TrackSection("straight", 200), TrackSection("corner", 100, radius=50), TrackSection("straight", 200), TrackSection("corner", 100, radius=50),
        ]
    }
}

def get_track(name: str) -> dict:
    """Returns a dictionary with all data for a given track name."""
    if name not in TRACK_DATA:
        raise ValueError(f"Track '{name}' not found.")
    
    theme = THEMES[name]
    track_info = TRACK_DATA[name]
    
    # The Track object from track.py now gets initialized with the sections
    track_physics = Track()
    track_physics.sections = track_info["sections"]
    track_physics.length = sum(s.length for s in track_physics.sections)

    return {
        "name": theme["name"],
        "theme": theme,
        "path": track_info["path"],
        "physics": track_physics
    }
