import numpy as np
from .base import Effect

class Reverb(Effect):
    """
    Schroeder Reverb: Classic algorithm using comb + allpass filters
    
    Key Concepts:
    - Comb filters: Create early reflections (parallel)
    - All-pass filters: Increase echo density (series)
    - Damping: High-frequency absorption (realistic rooms)
    - Multiple delay lines: Simulate room reflections
    
    This is a SIMPLIFIED reverb - pro reverbs use 20+ delay lines
    and sophisticated diffusion networks
    """
    
    def __init__(self, sample_rate):
        # Reverb parameters - set BEFORE super().__init__()
        self.room_size = 0.75      # 0-1: affects delay times
        self.damping = 0.5         # 0-1: high frequency absorption
        self.wet_level = 0.3       # Reverb amount
        self.dry_level = 0.7       # Direct signal amount
        
        # Comb filter delays (in samples) - these create the "room size"
        # Carefully chosen to be non-harmonic (avoid metallic resonance)
        # These are scaled by room_size
        self.comb_delays = [
            int(1557 * sample_rate / 44100),  # Scale to current sample rate
            int(1617 * sample_rate / 44100),
            int(1491 * sample_rate / 44100),
            int(1422 * sample_rate / 44100),
        ]
        
        # All-pass filter delays - these diffuse the sound
        self.allpass_delays = [
            int(225 * sample_rate / 44100),
            int(556 * sample_rate / 44100),
            int(441 * sample_rate / 44100),
            int(341 * sample_rate / 44100),
        ]
        
        super().__init__(sample_rate)
    
    def reset(self):
        # Comb filter buffers (parallel)
        self.comb_buffers = []
        self.comb_positions = []
        self.comb_filter_states = []  # For damping
        
        for delay in self.comb_delays:
            self.comb_buffers.append(np.zeros(delay, dtype='float32'))
            self.comb_positions.append(0)
            self.comb_filter_states.append(0.0)
        
        # All-pass filter buffers (series)
        self.allpass_buffers = []
        self.allpass_positions = []
        
        for delay in self.allpass_delays:
            self.allpass_buffers.append(np.zeros(delay, dtype='float32'))
            self.allpass_positions.append(0)
    
    @property
    def name(self):
        return "Reverb"
    
    def _process_comb_filter(self, input_sample, buffer, position, filter_state, index):
        """
        Comb Filter: Feedback delay line with damping
        
        Structure:
        Input → [+] → Delay → Damping Filter → [+] → Output
                ↑                               ↓
                └───────── Feedback ────────────┘
        
        The damping filter is a simple one-pole lowpass
        This simulates air absorption (high frequencies decay faster)
        """
        # Read delayed sample
        delayed = buffer[position]
        
        # Apply one-pole lowpass filter (damping)
        # This is a SIMPLIFIED room absorption model
        # Real rooms absorb highs more than lows
        filter_state = delayed * (1 - self.damping) + filter_state * self.damping
        
        # Calculate feedback
        feedback_gain = 0.7 * self.room_size
        
        # Write: input + filtered feedback
        buffer[position] = input_sample + filter_state * feedback_gain
        
        # Advance position
        position = (position + 1) % len(buffer)
        
        # Update filter state
        self.comb_filter_states[index] = filter_state
        
        return delayed, position
    
    def _process_allpass_filter(self, input_sample, buffer, position):
        """
        All-Pass Filter: Adds density without coloring
        
        Structure:
        Input → [+] → Delay → [×-g] → [+] → Output
                ↓                      ↑
                └──[×g]────────────────┘
        
        All-pass filters are AMAZING:
        - They add reflections (increase echo density)
        - They DON'T change frequency response (flat magnitude)
        - This makes reverb sound smooth, not metallic
        """
        # Read delayed sample
        delayed = buffer[position]
        
        # All-pass coefficient (typically 0.5-0.7)
        g = 0.5
        
        # All-pass formula
        # This specific structure maintains flat frequency response
        output = -input_sample + delayed
        buffer[position] = input_sample + delayed * g
        
        # Advance position
        position = (position + 1) % len(buffer)
        
        return output, position
    
    def process(self, audio, frames):
        """
        Process with Schroeder reverb structure
        
        Signal flow:
        Input → [Comb 1] ↘
                [Comb 2] → [+] → [AP1] → [AP2] → [AP3] → [AP4] → Output
                [Comb 3] ↗         ↑
                [Comb 4] ↗         └── Series diffusion
                  ↑
                  └── Parallel early reflections
        """
        out = np.empty_like(audio)
        
        for i in range(frames):
            input_sample = audio[i]
            
            # STAGE 1: Parallel comb filters (early reflections)
            # These create the initial "room response"
            comb_sum = 0.0
            for j in range(len(self.comb_buffers)):
                delayed, new_pos = self._process_comb_filter(
                    input_sample,
                    self.comb_buffers[j],
                    self.comb_positions[j],
                    self.comb_filter_states[j],
                    j
                )
                self.comb_positions[j] = new_pos
                comb_sum += delayed
            
            # Average the comb outputs
            comb_output = comb_sum / len(self.comb_buffers)
            
            # STAGE 2: Series all-pass filters (diffusion)
            # These make the reverb dense and smooth
            allpass_output = comb_output
            for j in range(len(self.allpass_buffers)):
                allpass_output, new_pos = self._process_allpass_filter(
                    allpass_output,
                    self.allpass_buffers[j],
                    self.allpass_positions[j]
                )
                self.allpass_positions[j] = new_pos
            
            # STAGE 3: Mix dry and wet
            out[i] = input_sample * self.dry_level + allpass_output * self.wet_level
        
        return out