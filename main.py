import time
import board
from adafruit_circuitplayground.express import cpx

import audiobusio
import array
import math
from digitalio import DigitalInOut, Direction
import touchio

import neopixel

OUTSIDE_PIXELS = neopixel.NeoPixel(board.D1, 8)
INSIDE_PIXELS = cpx.pixels

LEDStrip = DigitalInOut(board.A1)
LEDStrip.direction = Direction.OUTPUT

PINKISH = (255, 10, 187)
GREENISH = (187, 255, 10)
BLUEISH = (10, 187, 255)
ROXINHO = (175, 35, 255)
LARANJINHA = (255, 130, 10)
BLUEZAO = (10, 95, 255)

RED = (255, 0, 0)

# sample rate
SAMPLERATE = 8000
# how many samples we're collecting
NUM_SAMPLES = 160
mic = audiobusio.PDMIn(board.MICROPHONE_CLOCK,
                       board.MICROPHONE_DATA,
                       sample_rate=16000,
                       bit_depth=16)
samples = array.array('H', [0] * NUM_SAMPLES)


# Remove DC bias before computing RMS.
def normalized_rms(values):
    minbuf = int(mean(values))
    return math.sqrt(sum(float((sample - minbuf) * (sample - minbuf))
                         for sample in values) / len(values))


def mean(values):
    return (sum(values) / len(values))


def magnitude(x, y, z):
    return math.sqrt(x ** 2 + y ** 2 + z ** 2)


def print_sensors():
    print("Temperature: %0.1f *C" % cpx.temperature)
    print("Light Level: %d" % cpx.light)
    x, y, z = cpx.acceleration
    print("Accelerometer: (%0.1f, %0.1f, %0.1f) m/s^2" % (x, y, z))
    print("Module: %f" % magnitude(x, y, z))
    print('-' * 40)


def react_to_sound():
    mic.record(samples, len(samples))
    magnitude = normalized_rms(samples)
    # print the magnitude of the input blowing so we can track values
    # in the serial console
    print("(%f)" % magnitude)
    return magnitude


def normalize(ch):
    return min(0.05, max(abs(ch), 0.01))


def detect_change():
    x0, y0, z0 = cpx.acceleration
    prev = magnitude(x0, y0, z0)
    time.sleep(0.1)
    x, y, z = cpx.acceleration
    current = magnitude(x, y, z)

    change = current - prev
    return change, current


def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if (pos < 0) or (pos > 255):
        return (0, 0, 0)
    if pos < 85:
        return (int(255 - pos*3), int(pos*3), 0)
    elif pos < 170:
        pos -= 85
        return (0, int(255 - (pos*3)), int(pos*3))
    else:
        pos -= 170
    return (int(pos*3), 0, int(255 - pos*3))


# Main code start

SLEEP_TIME = 0.1  # seconds
QUIET_EPOCHS = 0
MAX_QUIET_EPOCHS = 600
EPOCH_INCREASE = 1
EPOCH_DECREASE = .5

MODE2_MAX_EPOCHS = 100
MOVE_THRESHOLD = 10
MOVE_CHANGE_THRESHOLD = 10.1
MOVEMENT_ACC = 0
MAX_MOVEMENT = 35

BLOW_THRESHOLD = 100.0

OUTSIDE_LIGHT = RED

INSIDE_COLORS = [PINKISH, GREENISH, BLUEISH, ROXINHO, LARANJINHA, BLUEZAO]
INSIDE_COLOR_POS = 0

MODE = 0
MAX_MODE = 3

MODES = [
    "listening",
    "light inside",
    "inside off, red outside",
    "turn off all lights"
]

while True:
    print('current mode:', MODE)
    change, current = detect_change()

    if MODE == 0:  # quiet, wait for sound
        INSIDE_PIXELS.brightness = 0
        OUTSIDE_PIXELS.brightness = 0
        LEDStrip.value = False
        mag = react_to_sound()
        
        # any time we get a sound with a magnitude greater than the
        # value of BLOW_THRESHOLD, trigger the current pitch
        # (can be changed at top where it is defined)
        if mag > BLOW_THRESHOLD:
            MODE = 1
        
        if abs(current) > MOVE_THRESHOLD:
            MODE = 2

    elif MODE == 1:
        INSIDE_PIXELS.brightness = 1.0

        # turn on inside LEDs
        LEDStrip.value = True

        # turn off outside pixels
        OUTSIDE_PIXELS.brightness = 0
        
        snd = react_to_sound()
        if snd > BLOW_THRESHOLD:
            INSIDE_COLOR_POS = (INSIDE_COLOR_POS + 1) % len(INSIDE_COLORS)
        INSIDE_PIXELS.fill(INSIDE_COLORS[INSIDE_COLOR_POS])

        if abs(current) > MOVE_THRESHOLD:
            MODE = 2
            QUIET_EPOCHS = 0
            MOVEMENT_ACC = 0
            OUTSIDE_PIXELS.brightness = 1.0
        elif QUIET_EPOCHS > MAX_QUIET_EPOCHS:
            QUIET_EPOCHS = 0
            MODE = 0
        elif abs(current) < MOVE_THRESHOLD:
            QUIET_EPOCHS += EPOCH_INCREASE

    elif MODE == 2:
        # turn off leds/inside light
        LEDStrip.value = False
        INSIDE_PIXELS.brightness = 0
        QUIET_EPOCHS += EPOCH_INCREASE
        MOVEMENT_ACC += abs(change)

        OUTSIDE_PIXELS.fill(OUTSIDE_LIGHT)
        OUTSIDE_PIXELS.brightness = 1

        if QUIET_EPOCHS > MODE2_MAX_EPOCHS:
            QUIET_EPOCHS = 0
            MODE = 0
            if MOVEMENT_ACC > MAX_MOVEMENT:
                MODE = 3
            else:
                MOVEMENT_ACC = 0

        # print_sensors()

    elif MODE == 3:
        OUTSIDE_PIXELS.brightness = 0
        QUIET_EPOCHS += EPOCH_INCREASE

        if QUIET_EPOCHS > MAX_QUIET_EPOCHS:
            QUIET_EPOCHS = 0
            MODE = 0

    print("(%.3f, %.3f, %.3f, %.3f, %.1f, %d)" % (OUTSIDE_PIXELS.brightness, change, normalize(change), current, QUIET_EPOCHS / 10, MOVEMENT_ACC))
    #print("(%.3f, %.3f, %.3f)" % (change, normalize(change), current))
    if MODE == 0:
        time.sleep(SLEEP_TIME * 2)
    else:
        time.sleep(SLEEP_TIME)
