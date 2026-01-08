from .base import Effect
import numpy as np
class QTronPlus(Effect):
    """
    Simplified Electro-Harmonix Q-Tron+ envelope filter
    """

    def __init__(
        self,
        sample_rate,
        sensitivity=1.5,
        min_freq=200,
        max_freq=3000,
        resonance=0.8
    ):
        self.sensitivity = sensitivity
        self.min_freq = min_freq
        self.max_freq = max_freq
        self.resonance = resonance
        super().__init__(sample_rate)

    def reset(self):
        self.env = 0.0
        self.attack = 0.01
        self.release = 0.001

        # Filter state
        self.z1 = 0.0
        self.z2 = 0.0

    def process(self, audio, frames):
        output = np.zeros(frames)

        for i in range(frames):
            x = audio[i]

            # Envelope follower
            rect = abs(x)
            if rect > self.env:
                self.env += self.attack * (rect - self.env)
            else:
                self.env += self.release * (rect - self.env)

            # Envelope → cutoff frequency
            sweep = min(self.env * self.sensitivity, 1.0)
            cutoff = self.min_freq + sweep * (self.max_freq - self.min_freq)

            # Band-pass filter (state-variable)
            f = 2 * np.sin(np.pi * cutoff / self.sample_rate)
            hp = x - self.z1 - self.resonance * self.z2
            bp = f * hp + self.z2
            lp = f * bp + self.z1

            self.z2 = bp
            self.z1 = lp

            output[i] = bp

        return output
