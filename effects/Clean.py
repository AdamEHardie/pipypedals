from .base import Effect

class Clean(Effect):
    @property
    def name(self):
        return "Clean"

    def process(self, audio, frames):
        return audio