from .base import Effect
import numpy as np

class WildBlueChords(Effect):
    """
    John Mayer 'Wild Blue' chord tone:
    clean, wide, slow chorus, warm highs
    """

    def reset(self):
        # ======================
        # Compressor (very light)
        # ======================
        self.env = 0.0
        self.comp_attack = 0.01
        self.comp_release = 0.002
        self.comp_threshold = 0.25
        self.comp_ratio = 2.0

        # ======================
        # Chorus (delay modulation)
        # ======================
        self.max_delay_ms = 25
        self.depth_ms = 8
        self.rate_hz = 0.25  # slow swirl

        self.delay_samples = int(
            self.sample_rate * self.max_delay_ms / 1000
        )
        self.buffer = np.zeros(self.delay_samples)
        self.write_idx = 0
        self.lfo_phase = 0.0

        # ======================
        # Low-pass filter (warmth)
        # ======================
        self.lpf_alpha = 0.07
        self.lpf_state = 0.0

        # ======================
        # Mix & output
        # ======================
        self.mix = 0.4
        self.output_gain = 0.9

    @property
    def name(self):
        return "Wild Blue Chords"

    def process(self, audio, frames):
        out = np.zeros_like(audio)

        for i in range(frames):
            x = audio[i]

            # ======================
            # 1. Light compression
            # ======================
            level = abs(x)
            if level > self.env:
                self.env += self.comp_attack * (level - self.env)
            else:
                self.env += self.comp_release * (level - self.env)

            if self.env > self.comp_threshold:
                gain = (
                    self.comp_threshold +
                    (self.env - self.comp_threshold) / self.comp_ratio
                ) / self.env
                x *= gain

            # ======================
            # 2. Chorus LFO
            # ======================
            lfo = 0.5 * (1 + np.sin(2 * np.pi * self.lfo_phase))
            self.lfo_phase += self.rate_hz / self.sample_rate
            if self.lfo_phase >= 1.0:
                self.lfo_phase -= 1.0

            delay = int(
                (self.max_delay_ms - self.depth_ms * lfo)
                * self.sample_rate / 1000
            )

            read_idx = (self.write_idx - delay) % self.delay_samples
            delayed = self.buffer[read_idx]

            self.buffer[self.write_idx] = x
            self.write_idx = (self.write_idx + 1) % self.delay_samples

            # Mix dry + wet
            x = (1 - self.mix) * x + self.mix * delayed

            # ======================
            # 3. Low-pass filter
            # ======================
            self.lpf_state += self.lpf_alpha * (x - self.lpf_state)
            x = self.lpf_state

            # ======================
            # 4. Output soft limit
            # ======================
            out[i] = np.tanh(x * self.output_gain)

        return out
