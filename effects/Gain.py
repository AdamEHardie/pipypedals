from .base import Effect

class Gain(Effect):
    @property
    def name(self):
        return "Gain"

    def process(self, audio, frames):
        out = audio * -20.0
        print("before")
        print(audio)
        print("after")
        print(out)
        return out