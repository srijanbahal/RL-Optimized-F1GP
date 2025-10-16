class TrackSection:
    def __init__(self, kind, length, radius=None, drs=False):
        self.kind = kind          # "straight" or "corner"
        self.length = length      # metres
        self.radius = radius      # m, only for corners
        self.drs = drs            # bool

class Track:
    def __init__(self):
        self.sections = [
            TrackSection("straight", 800, drs=True),
            TrackSection("corner", 250, radius=80),
            TrackSection("straight", 1000),
            TrackSection("corner", 200, radius=60),
            TrackSection("straight", 900, drs=True),
        ]
        self.length = sum(s.length for s in self.sections)
        self.checkpoints = len(self.sections)

    def section_at(self, pos):
        p = pos % self.length
        cum = 0
        for sec in self.sections:
            cum += sec.length
            if p <= cum:
                return sec
        return self.sections[-1]
