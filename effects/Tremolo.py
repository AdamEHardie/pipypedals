import numpy as np
from .base import Effect

class Tremolo(Effect):
    """
    Tremolo: Periodic variation in amplitude
    
    Key Concepts:
    - LFO (Low Frequency Oscillator): generates a control signal
    - Modulation: using one signal to control another
    - Phase accumulation: tracking oscillator position
    """
    
    def __init__(self, sample_rate):
        # Tremolo parameters - set BEFORE super().__init__()
        self.rate = 5.0        # LFO frequency in Hz (how fast it wobbles)
        self.depth = 0.5       # 0.0 to 1.0 (how much volume change)
        self.waveform = 'sine' # 'sine', 'triangle', 'square'
        
        super().__init__(sample_rate)
    
    def reset(self):
        self.phase = 0.0  # Current position in the LFO waveform (0 to 2π)
    
    @property
    def name(self):
        return "Tremolo"
    
    def _generate_lfo_sample(self):
        """
        Generate one sample of the LFO waveform
        
        This is the heart of modulation effects!
        The LFO creates a control signal that modulates another parameter
        """
        if self.waveform == 'sine':
            # Sine wave: smooth, natural sounding
            # Goes from -1 to +1
            lfo = np.sin(self.phase)
        
        elif self.waveform == 'triangle':
            # Triangle wave: linear ramps up and down
            # Normalize phase to 0-1 range
            phase_norm = self.phase / (2 * np.pi)
            if phase_norm < 0.5:
                lfo = 4 * phase_norm - 1  # Rising edge
            else:
                lfo = 3 - 4 * phase_norm  # Falling edge
        
        elif self.waveform == 'square':
            # Square wave: abrupt on/off (helicopter effect)
            lfo = 1.0 if np.sin(self.phase) >= 0 else -1.0
        
        else:
            lfo = np.sin(self.phase)
        
        return lfo
    
    def process(self, audio, frames):
        """
        Process audio buffer sample-by-sample
        
        Key insight: We need sample-by-sample processing for smooth modulation
        Block processing would create audible steps
        """
        out = np.empty_like(audio)
        
        # Calculate how much to advance phase per sample
        # This determines the LFO frequency
        phase_increment = 2 * np.pi * self.rate / self.sample_rate
        
        for i in range(frames):
            # Generate LFO value for this sample (-1 to +1)
            lfo = self._generate_lfo_sample()
            
            # Convert LFO to amplitude multiplier
            # Map from [-1, +1] to [1-depth, 1+depth]
            # This creates the "tremolo" effect
            amplitude = 1.0 + (lfo * self.depth)
            
            # Apply amplitude modulation
            out[i] = audio[i] * amplitude
            
            # Advance the LFO phase
            self.phase += phase_increment
            
            # Wrap phase to stay in 0 to 2π range
            # Important: prevents numerical drift over time
            if self.phase >= 2 * np.pi:
                self.phase -= 2 * np.pi
        
        return out