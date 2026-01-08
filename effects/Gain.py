from .base import Effect

class Gain(Effect):
    @property
    def name(self):
        return "Gain"

    def process(self, audio, frames):
        out = audio * 10.0
        return out