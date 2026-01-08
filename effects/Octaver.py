from .base import Effect
import numpy as np

class Octaver(Effect):
    @property
    def name(self):
        return "Octaver"

    def process(self, audio, frames):
        """
        Processes the audio signal to add an octave effect.

        Parameters:
        audio (numpy.ndarray): The input audio signal.
        frames (int): The number of frames in the audio signal.

        Returns:
        numpy.ndarray: The processed audio signal with the octave effect.
        """
        # Ensure the audio is a numpy array
        audio = np.asarray(audio)

        # Create an octave-down effect by halving the frequency
        octave_down = np.interp(
            np.linspace(0, len(audio), len(audio) // 2, endpoint=False),
            np.arange(len(audio)),
            audio
        )

        # Duplicate the octave-down signal to match the original length
        octave_down = np.tile(octave_down, 2)[:len(audio)]

        # Mix the original signal with the octave-down signal
        processed_audio = (audio + octave_down) / 2
        return processed_audio