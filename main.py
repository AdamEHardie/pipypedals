import sounddevice as sd
import numpy as np
import time
import threading

print(sd.query_devices())
# scarlet seems to be on port 1
SAMPLE_RATE = 48000
BUFFER_SIZE = 128

INPUT_DEVICE = 1
OUTPUT_DEVICE = 1

# EFFECT PARAMS
GAIN_BOOST = 10.0
LPF_COEFF = 0.1
prev_lpf = 0.0

DIST_GAIN = 20.0

# ECHO PARAMS
ECHO_DELAY_MS = 350
ECHO_FEEDBACK = 0.35
ECHO_MIX = 0.5
ECHO_MAX_SECTIONS = 2.0

# CONVERT DELAY TO SAMPLES 
echo_delay_samples = int(SAMPLE_RATE * (ECHO_DELAY_MS / 1000.0))
echo_buffer_size = int(SAMPLE_RATE * ECHO_MAX_SECTIONS)

# circular delay buffer + write pointer
echo_buffer = np.zeros(echo_buffer_size, dtype="float32")
echo_write_idx = 0

# current effect
current_fx = 0
running = True

def audio_callback(indata, outdata, frames, time_data, status):
    global prev_lpf, current_fx
    global echo_buffer, echo_write_idx

    audio = indata[:, 0]

    if current_fx == 0:
        out = audio
    elif current_fx == 1:
        out = np.zeros_like(audio)
        for i in range(frames):
            read_idx = (echo_write_idx - echo_delay_samples) % echo_buffer_size
            delayed_sample = echo_buffer[read_idx]

            dry = audio[i]
            wet = delayed_sample
            out_sample = (1.0 - ECHO_MIX) * dry + ECHO_MIX * wet
            out[i] = out_sample

            echo_buffer[echo_write_idx] = dry + delayed_sample * ECHO_FEEDBACK

            echo_write_idx = (echo_write_idx + 1) % echo_buffer_size
    else:
        out = audio
    
    outdata[:] = out.reshape(-1, 1)

def cli_menu():
    global current_fx, running
    print("guitar pedals:")
    print("1 - clean")
    print("2 - echo")
    print("q - quit")

    while running:
        choice = input("> ").strip()

        if choice == "1":
            current_fx = 0
            print("clean effect")
        elif choice == "2":
            current_fx = 1
            print("echo")
        elif choice == "q":
            running = False
        else:
            print("unknown")

print("starting effects....")
threading.Thread(target=cli_menu, daemon=True).start()

try:
    with sd.Stream(
        samplerate=SAMPLE_RATE,
        blocksize=BUFFER_SIZE,
        dtype="float32",
        channels=1,
        callback=audio_callback,
        device=(INPUT_DEVICE, OUTPUT_DEVICE),
        latency="low",
    ):
        while running:
            time.sleep(0.1)
except KeyboardInterrupt:
    running= False
    print("stopped")