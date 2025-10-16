class Track:
    def __init__(self, length: float = 1000.0, checkpoints: int = 20):
        self.length = length
        self.checkpoints = checkpoints
        self.segment_length = length / checkpoints

    def is_finished(self, position: float) -> bool:
        return position >= self.length
