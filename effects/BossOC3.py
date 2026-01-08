import numpy as np
from .base import Effect
class BossOC3(Effect):
    """
    Simplified Boss OC-3 style octave-down effect
    (analog-style octave via rectification)
    """

    def __init__(self, sample_rate, sub_level=1.0, clean_level=0.5):
        self.sub_level = sub_level
        self.clean_level = clean_level
        super().__init__(sample_rate)

    def reset(self):
        self.lp_state = 0.0
        self.lp_coeff = 0.01  # smoothing factor

    def process(self, audio, frames):
        output = np.zeros(frames)

        for i in range(frames):
            x = audio[i]

            # Full-wave rectification creates octave-down harmonic
            rectified = abs(x)

            # Low-pass filter to smooth into sub-octave
            self.lp_state += self.lp_coeff * (rectified - self.lp_state)
            sub_octave = self.lp_state * 2.0 - 1.0

            output[i] = (
                self.clean_level * x +
                self.sub_level * sub_octave
            )

        return output
