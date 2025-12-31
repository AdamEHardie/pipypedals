import numpy as np
from .base import Effect

class WahWah(Effect):
    def __init__(self, sample_rate):
        super().__init__(sample_rate)
        # Wah parameters
        self.lfo_freq = 0.5  # LFO frequency in Hz (speed of wah sweep)
        self.min_freq = 400  # Minimum filter frequency
        self.max_freq = 2500  # Maximum filter frequency
        self.q_factor = 5.0  # Resonance (higher = more pronounced wah)
        
    def reset(self):
        # LFO phase
        self.phase = 0.0
        # Biquad filter state variables
        self.x1 = 0.0
        self.x2 = 0.0
        self.y1 = 0.0
        self.y2 = 0.0
    
    @property
    def name(self):
        return "Wah-Wah"
    
    def _calculate_biquad_coeffs(self, center_freq):
        """Calculate biquad bandpass filter coefficients"""
        w0 = 2 * np.pi * center_freq / self.sample_rate
        alpha = np.sin(w0) / (2 * self.q_factor)
        
        # Bandpass filter coefficients
        b0 = alpha
        b1 = 0.0
        b2 = -alpha
        a0 = 1 + alpha
        a1 = -2 * np.cos(w0)
        a2 = 1 - alpha
        
        # Normalize
        b0 /= a0
        b1 /= a0
        b2 /= a0
        a1 /= a0
        a2 /= a0
        
        return b0, b1, b2, a1, a2
    
    def process(self, audio, frames):
        out = np.empty_like(audio)
        
        phase_increment = 2 * np.pi * self.lfo_freq / self.sample_rate
        
        for i in range(frames):
            # LFO creates sweep from min to max frequency
            lfo = 0.5 * (1 + np.sin(self.phase))
            center_freq = self.min_freq + lfo * (self.max_freq - self.min_freq)
            
            # Calculate filter coefficients for current center frequency
            b0, b1, b2, a1, a2 = self._calculate_biquad_coeffs(center_freq)
            
            # Apply biquad filter (Direct Form II)
            x = audio[i]
            y = b0 * x + b1 * self.x1 + b2 * self.x2 - a1 * self.y1 - a2 * self.y2
            
            # Update state
            self.x2 = self.x1
            self.x1 = x
            self.y2 = self.y1
            self.y1 = y
            
            out[i] = y
            
            # Advance LFO phase
            self.phase += phase_increment
            if self.phase >= 2 * np.pi:
                self.phase -= 2 * np.pi
        
        return out