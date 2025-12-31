import numpy as np
from .base import Effect

class Looper(Effect):
    def __init__(self, sample_rate):
        self.max_loop_seconds = 30.0  # Maximum loop length
        self.max_loop_samples = int(self.max_loop_seconds * sample_rate)

        # Metronome / count-in defaults - set BEFORE calling super().__init__
        self.default_bpm = 120
        self.default_count_beats = 4
        self.default_click_freq = 1000.0
        self.default_click_duration = 0.02  # seconds
        self.default_click_amp = 0.8

        # Prepare click buffer (will be (re)created in start_recording)
        self.click_buffer = None

        super().__init__(sample_rate)
        # note: base.__init__ calls reset(), so no need to call self.reset() again here

    def reset(self):
        # Loop buffer
        self.loop_buffer = np.zeros(self.max_loop_samples, dtype='float32')
        self.loop_length = 0
        self.loop_position = 0

        # States
        self.is_recording = False
        self.is_playing = False
        self.record_position = 0

        # Count-in / metronome states
        self.is_counting_in = False
        # use existing defaults (set before super().__init__)
        self.count_in_bpm = self.default_bpm
        self.count_in_beats_total = self.default_count_beats
        self.count_in_beats_remaining = 0
        self.beat_interval_samples = 0
        self.count_in_samples_to_next_click = 0
        self.count_in_start_delay_remaining = 0  # delay after last click before starting recording
        self.click_buffer = None
        self.click_pos = 0

    @property
    def name(self):
        return "Looper"

    def _make_click_buffer(self, freq=None, duration=None, amp=None):
        # Create a short sine burst click with a Hann window
        freq = freq or self.default_click_freq
        duration = duration or self.default_click_duration
        amp = amp if amp is not None else self.default_click_amp
        length = max(1, int(duration * self.sample_rate))
        t = np.arange(length) / float(self.sample_rate)
        sine = np.sin(2.0 * np.pi * freq * t)
        window = np.hanning(length)
        click = (sine * window * amp).astype('float32')
        return click

    def start_recording(self, bpm=None, beats=None, click_freq=None, click_duration=None, click_amp=None):
        """Start a count-in then record a new loop.
        Defaults: bpm=120, beats=4 (4-beat count-in).
        """
        # Reset loop state before a new recording
        self.reset()

        # Configure count-in / metronome
        self.count_in_bpm = bpm or self.default_bpm
        self.count_in_beats_total = beats or self.default_count_beats
        self.count_in_beats_remaining = self.count_in_beats_total
        self.beat_interval_samples = max(1, int((60.0 / float(self.count_in_bpm)) * self.sample_rate))
        self.count_in_samples_to_next_click = 0  # trigger a click immediately
        self.click_buffer = self._make_click_buffer(click_freq, click_duration, click_amp)
        self.click_pos = 0
        self.count_in_start_delay_remaining = 0
        self.is_counting_in = True
        self.is_recording = False
        self.is_playing = False
        self.record_position = 0

        return f"Count-in {self.count_in_beats_total} beats at {self.count_in_bpm} BPM..."

    def stop_recording(self):
        """Stop recording and start playback"""
        # If we are counting-in, cancel and do not create a loop
        if self.is_counting_in:
            self.is_counting_in = False
            self.record_position = 0
            return "Count-in cancelled"

        if self.is_recording and self.record_position > 0:
            self.loop_length = self.record_position
            self.is_recording = False
            self.is_playing = True
            self.loop_position = 0
            duration = self.loop_length / self.sample_rate
            return f"Loop saved ({duration:.1f}s) - Playing back"
        return "No loop recorded"

    def stop_playback(self):
        """Stop loop playback"""
        self.is_playing = False
        return "Loop stopped"

    def toggle_playback(self):
        """Toggle playback on/off (keep loop in memory)"""
        if self.loop_length > 0:
            self.is_playing = not self.is_playing
            return "Playing" if self.is_playing else "Paused"
        return "No loop to play"

    def clear_loop(self):
        """Clear the current loop"""
        self.reset()
        return "Loop cleared"

    def get_status(self):
        """Get current looper status"""
        if self.is_counting_in:
            return f"COUNTIN [{self.count_in_beats_remaining} beats]"
        if self.is_recording:
            duration = self.record_position / self.sample_rate
            return f"REC [{duration:.1f}s]"
        elif self.is_playing and self.loop_length > 0:
            duration = self.loop_length / self.sample_rate
            position = self.loop_position / self.sample_rate
            return f"PLAY [{position:.1f}/{duration:.1f}s]"
        elif self.loop_length > 0:
            duration = self.loop_length / self.sample_rate
            return f"PAUSED [{duration:.1f}s]"
        else:
            return "EMPTY"

    def process(self, audio, frames):
        out = np.zeros_like(audio)

        for i in range(frames):
            input_sample = audio[i]
            output_sample = input_sample

            # === Count-in / metronome handling ===
            click_sample = 0.0
            if self.is_counting_in:
                # If it's time to trigger a click
                if self.count_in_samples_to_next_click <= 0 and self.count_in_beats_remaining > 0:
                    # Trigger click
                    self.click_pos = 0
                    # After triggering a click, schedule next click after beat interval
                    self.count_in_samples_to_next_click = self.beat_interval_samples
                    # Decrement beats remaining (this click counts as one beat)
                    self.count_in_beats_remaining -= 1
                    # If that was the last beat, schedule a short delay equal to click length before starting recording
                    if self.count_in_beats_remaining == 0:
                        self.count_in_start_delay_remaining = len(self.click_buffer)

                # Decrement timer to next click
                self.count_in_samples_to_next_click -= 1

                # If click is playing, add click buffer sample
                if self.click_buffer is not None and self.click_pos < len(self.click_buffer):
                    click_sample = float(self.click_buffer[self.click_pos])
                    self.click_pos += 1

                # If we have finished the final click and its delay, begin recording
                if (self.count_in_beats_remaining == 0) and (self.count_in_start_delay_remaining > 0):
                    self.count_in_start_delay_remaining -= 1
                    if self.count_in_start_delay_remaining == 0:
                        # Start recording now
                        self.is_counting_in = False
                        self.is_recording = True
                        self.is_playing = False
                        self.record_position = 0
                # Mix click into output (count-in should be audible)
                output_sample = input_sample + click_sample

            else:
                # === Recording behavior ===
                if self.is_recording:
                    # Record input into buffer
                    if self.record_position < self.max_loop_samples:
                        self.loop_buffer[self.record_position] = input_sample
                        self.record_position += 1
                    else:
                        # Auto-stop if max length reached
                        self.stop_recording()
                    output_sample = input_sample  # pass-through while recording

                # === Playback behavior ===
                if self.is_playing and self.loop_length > 0:
                    loop_sample = self.loop_buffer[self.loop_position]
                    output_sample = input_sample + loop_sample  # Mix input with loop
                    # Advance loop position
                    self.loop_position = (self.loop_position + 1) % self.loop_length

            out[i] = output_sample

        return out