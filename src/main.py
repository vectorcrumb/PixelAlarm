from machine import I2C, Pin
from random import randint
import neopixel, time
from DS3231 import DS3231


def bbutton_irq_handler(pin):
    print("Blue Button Pressed!")

def ybutton_irq_handler(pin):
    print("Yellow button pressed!")

# Constants
TEMP_SAFETY_LIMIT = 45
PRE_WAKEUP_PERIOD = 30
POST_WAKEUP_PERIOD = 15
IDLE_TIME_PERIOD = 15
WAKEUP_COLOR = (0.529, 0.808, 0.98)
ALARM = [7, 30]
# Pin Definitions
PIN_NEOPIXELS = 16
PIN_RTC_SDA = 21
PIN_RTC_SCL = 22
PIN_BUTTON_BLUE = 23
PIN_BUTTON_YELLOW = 5
# Neopixels. Index incs. from right to left, bottom to top (double flipped cartesian)
n_cols, n_rows = 8, 8
n_pixels = n_cols * n_rows
np = neopixel.NeoPixel(Pin(PIN_NEOPIXELS), n_pixels)
# RTC. To set time, use the following line:
# ds.DateTime([2019, 12, 15, 7, 14, 5, 30])
# Sets 15 Dec 2019, 2:05:30 PM
i2c = I2C(sda=Pin(PIN_RTC_SDA), scl=Pin(PIN_RTC_SCL))
rtc = DS3231(i2c)
# Buttons
button_blue = Pin(PIN_BUTTON_BLUE, Pin.IN, Pin.PULL_UP)
button_yellow = Pin(PIN_BUTTON_YELLOW, Pin.IN, Pin.PULL_UP)

button_blue.irq(bbutton_irq_handler, trigger=Pin.IRQ_FALLING)
button_yellow.irq(ybutton_irq_handler, trigger=Pin.IRQ_FALLING)


def neopixels_to_val(npixels, value, pixel_list=[], pixel_cnt=64):
    idxs = range(pixel_cnt) if pixel_list == [] else pixel_list
    for i in idxs:
        npixels[i] = value
    npixels.write()

def neopixels_off(npixels, pixel_list=[], pixel_cnt=64):
    neopixels_to_val(npixels, (0, 0, 0), pixel_list=pixel_list, pixel_cnt=pixel_cnt)

def check_temp(temp_val):
    if temp_val > TEMP_SAFETY_LIMIT:
        print("Temperature limit passed! Current temperature is {}".format(temp_val))
        neopixels_off(np)
        return True
    return False


# Time is stored in minutes since midnight, for a max of 24*60=1440.
alarm_time = ALARM[0] * 60 + ALARM[1]
waking = False
on_leds = 0
brightness_values = [int(i * (255 / PRE_WAKEUP_PERIOD)) for i in range(PRE_WAKEUP_PERIOD + 1)][1:]
neopixels_off(np)

while True:
    # Safety Check. Measure temp to avoid burning up
    if check_temp(rtc.Temperature()):
        break
    # Decide if waking or not
    if waking:
        # Upon waking, we have PRE_WAKEUP_PERIOD minutes available
        # During this time, we turn on LEDs
        print("Waking up!")
        for curr_brightness in brightness_values:
            if check_temp(rtc.Temperature()):
                break
            if curr_brightness > 150:
                break
            curr_color = tuple([int(curr_brightness * rgb_percentage) for rgb_percentage in WAKEUP_COLOR])
            neopixels_to_val(np, curr_color)
            print("Setting value to {} for brightness of {}".format(curr_color, curr_brightness))
            time.sleep(60)
        # Waking process is done
        print("Finished waking up!")
        neopixels_off(np)
        waking = False
    else:
        # Calculate current minute time
        curr_time = rtc.Time()
        curr_min = curr_time[0] * 60 + curr_time[1]
        print("Time is {}:{}".format(*curr_time))
        # If time is in interval between [alarm - pre_wu, alarm + post_wu[
        if curr_min >= (alarm_time - PRE_WAKEUP_PERIOD) and curr_min < (alarm_time - 5):
            print("Waking up for alarm at {}:{}".format(*ALARM))
            waking = True
        # If not and not waking, we should simply idle. This can be later used for other tasks
        else:
            time.sleep(IDLE_TIME_PERIOD)
