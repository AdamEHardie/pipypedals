import numpy as np
from config import SAMPLE_RATE, ECHO_DELAY_MS, ECHO_FEEDBACK, ECHO_MIX, ECHO_MAX_SECTIONS
from .base import Effect

class Echo(Effect):
    def reset(self):
        self.echo_delay_samples = int(self.sample_rate * (ECHO_DELAY_MS / 1000.0))
        self.echo_buffer_size = int(self.sample_rate * ECHO_MAX_SECTIONS)
        self.echo_buffer = np.zeros(self.echo_buffer_size, dtype="float32")
        self.echo_write_idx = 0

    @property
    def name(self):
        return "Echo"

    def process(self, audio, frames):
        out = np.zeros_like(audio)
        for i in range(frames):
            read_idx = (self.echo_write_idx - self.echo_delay_samples) % self.echo_buffer_size
            delayed_sample = self.echo_buffer[read_idx]

            dry = audio[i]
            wet = delayed_sample

            out_sample = (1.0 - ECHO_MIX) * dry + ECHO_MIX * wet
            out[i] = out_sample

            self.echo_buffer[self.echo_write_idx] = dry + delayed_sample * ECHO_FEEDBACK

            self.echo_write_idx = (self.echo_write_idx + 1) % self.echo_buffer_size
        
        return out