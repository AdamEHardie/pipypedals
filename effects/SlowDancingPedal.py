from .base import Effect
import numpy as np

class SlowDancingPedal(Effect):
    """
    John Mayer 'Slow Dancing in a Burning Room' style pedal
    """

    def reset(self):
        # --- Compressor state ---
        self.env = 0.0
        self.comp_attack = 0.01
        self.comp_release = 0.003
        self.comp_threshold = 0.2
        self.comp_ratio = 3.0

        # --- Low-pass tone filter ---
        self.lpf_state = 0.0
        self.lpf_alpha = 0.08

        # --- Delay (slapback) ---
        self.delay_ms = 120
        self.delay_samples = int(self.sample_rate * self.delay_ms / 1000)
        self.delay_buffer = np.zeros(int(self.sample_rate * 1.0), dtype=np.float32)
        self.delay_idx = 0
        self.delay_mix = 0.18
        self.delay_feedback = 0.25

    @property
    def name(self):
        return "Slow Dancing Pedal"

    def process(self, audio, frames):
        out = np.zeros_like(audio)

        for i in range(frames):
            x = audio[i]

            # =========================
            # 1. Compressor
            # =========================
            rectified = abs(x)

            if rectified > self.env:
                self.env += self.comp_attack * (rectified - self.env)
            else:
                self.env += self.comp_release * (rectified - self.env)

            gain = 1.0
            if self.env > self.comp_threshold:
                gain = (self.comp_threshold + 
                        (self.env - self.comp_threshold) / self.comp_ratio) / self.env

            x *= gain

            # =========================
            # 2. Low-gain Overdrive
            # =========================
            drive = 2.2
            x = np.tanh(x * drive)

            # =========================
            # 3. Tone (Low-pass)
            # =========================
            self.lpf_state += self.lpf_alpha * (x - self.lpf_state)
            x = self.lpf_state

            # =========================
            # 4. Slapback Delay
            # =========================
            read_idx = (self.delay_idx - self.delay_samples) % len(self.delay_buffer)
            delayed = self.delay_buffer[read_idx]

            # write delay with feedback
            self.delay_buffer[self.delay_idx] = x + delayed * self.delay_feedback
            self.delay_idx = (self.delay_idx + 1) % len(self.delay_buffer)

            # mix dry + wet
            x = (1.0 - self.delay_mix) * x + self.delay_mix * delayed

            out[i] = x

        return out
