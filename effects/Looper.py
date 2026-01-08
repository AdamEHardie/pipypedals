import numpy as np
from .base import Effect


class Looper(Effect):
    def __init__(self, sample_rate):
        self.sample_rate = sample_rate
        self.max_loop_seconds = 30.0
        self.max_loop_samples = int(self.max_loop_seconds * sample_rate)

        # Defaults
        self.default_bpm = 120
        self.default_count_beats = 5
        self.default_click_freq = 1000.0
        self.default_click_duration = 0.02
        self.default_click_amp = 0.8

        # Mix
        self.monitor_gain = 1.0   # live input
        self.loop_gain = 1.0      # loop playback

        super().__init__(sample_rate)
        self.reset()

    # ------------------------------------------------
    # State
    # ------------------------------------------------
    def reset(self):
        self.loop_buffer = np.zeros(self.max_loop_samples, dtype=np.float32)
        self.loop_length = 0
        self.loop_position = 0

        self.is_recording = False
        self.is_playing = False
        self.is_counting_in = False

        self.record_position = 0

        # Count-in
        self.count_in_beats_remaining = 0
        self.beat_interval_samples = 0
        self.samples_to_next_click = 0
        self.click_buffer = None
        self.click_pos = 0

    @property
    def name(self):
        return "Looper"

    # ------------------------------------------------
    # Click
    # ------------------------------------------------
    def _make_click_buffer(self, freq, duration, amp):
        length = max(1, int(duration * self.sample_rate))
        t = np.arange(length) / self.sample_rate
        click = np.sin(2.0 * np.pi * freq * t)
        click *= np.hanning(length)
        return ((click * amp).astype(np.float32)) * 0.5

    # ------------------------------------------------
    # Controls (PEDAL BEHAVIOR)
    # ------------------------------------------------
    def start_recording(self, bpm=None, beats=None):
        """
        Pedal behavior:
        - idle        -> start count-in
        - counting in -> cancel
        - recording   -> stop recording
        """

        # Stop recording on second press
        if self.is_recording:
            return self.stop_recording()

        # Cancel count-in
        if self.is_counting_in:
            self.is_counting_in = False
            return "Count-in cancelled"

        # Fresh record
        self.reset()

        bpm = bpm or self.default_bpm
        beats = beats or self.default_count_beats

        self.beat_interval_samples = int((60.0 / bpm) * self.sample_rate)
        self.count_in_beats_remaining = beats
        self.samples_to_next_click = 0

        self.click_buffer = self._make_click_buffer(
            self.default_click_freq,
            self.default_click_duration,
            self.default_click_amp,
        )
        self.click_pos = 0
        self.is_counting_in = True

        return f"Count-in {beats} beats @ {bpm} BPM"

    def stop_recording(self):
        if not self.is_recording or self.record_position == 0:
            self.is_recording = False
            return "Nothing recorded"

        self.loop_length = self.record_position
        self.is_recording = False
        self.is_playing = True
        self.loop_position = 0

        self._apply_crossfade()

        dur = self.loop_length / self.sample_rate
        return f"Loop captured ({dur:.2f}s)"

    def toggle_playback(self):
        if self.loop_length == 0:
            return "No loop"
        self.is_playing = not self.is_playing
        return "Playing" if self.is_playing else "Paused"

    def clear_loop(self):
        self.reset()
        return "Cleared"

    # ------------------------------------------------
    # Status (for CLI)
    # ------------------------------------------------
    def get_status(self):
        if self.is_counting_in:
            return f"COUNT-IN ({self.count_in_beats_remaining} beats)"
        if self.is_recording:
            dur = self.record_position / self.sample_rate
            return f"REC {dur:.2f}s"
        if self.is_playing and self.loop_length > 0:
            pos = self.loop_position / self.sample_rate
            dur = self.loop_length / self.sample_rate
            return f"PLAY {pos:.2f}/{dur:.2f}s"
        if self.loop_length > 0:
            dur = self.loop_length / self.sample_rate
            return f"PAUSED {dur:.2f}s"
        return "EMPTY"

    # ------------------------------------------------
    # DSP helpers
    # ------------------------------------------------
    def _apply_crossfade(self, fade_samples=64):
        if self.loop_length < fade_samples * 2:
            return

        fade = np.linspace(0.0, 1.0, fade_samples)
        self.loop_buffer[:fade_samples] *= fade
        self.loop_buffer[
            self.loop_length - fade_samples : self.loop_length
        ] *= (1.0 - fade)

    # ------------------------------------------------
    # Audio processing
    # ------------------------------------------------
    def process(self, audio, frames):
        out = np.zeros_like(audio)

        for i in range(frames):
            inp = audio[i]
            loop_sample = 0.0
            click_sample = 0.0

            # ---------- COUNT-IN ----------
            if self.is_counting_in:
                self.samples_to_next_click -= 1

                if self.samples_to_next_click <= 0 and self.count_in_beats_remaining > 0:
                    self.samples_to_next_click = self.beat_interval_samples
                    self.count_in_beats_remaining -= 1
                    self.click_pos = 0

                    # Start recording on the final beat
                    if self.count_in_beats_remaining == 0:
                        self.is_recording = True
                        self.record_position = 0

                if self.click_pos < len(self.click_buffer):
                    click_sample = self.click_buffer[self.click_pos]
                    self.click_pos += 1

                if self.is_recording:
                    self.is_counting_in = False

                out[i] = click_sample
                continue

            # ---------- RECORD ----------
            if self.is_recording:
                if self.record_position < self.max_loop_samples:
                    self.loop_buffer[self.record_position] = inp
                    self.record_position += 1

            # ---------- PLAY ----------
            if self.is_playing and self.loop_length > 0:
                loop_sample = self.loop_buffer[self.loop_position]
                self.loop_position += 1
                if self.loop_position >= self.loop_length:
                    self.loop_position = 0

            # ---------- MIX ----------
            mixed = (loop_sample * self.loop_gain) + (inp * self.monitor_gain)

            # Soft limiter for safety
            out[i] = np.tanh(mixed)

        return out
