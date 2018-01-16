import os
import ujson
from utime import sleep_us, sleep_ms
from machine import Pin, PWM, ADC, time_pulse_us

# LEDs
STATUS = 0
OPPONENT = 1
LEFT_LINE = 2
RIGHT_LINE = 3

# directions
STOP = 0
LEFT = 1
RIGHT = 2
FORWARD = 3
BACKWARD = 4

# open and parse the config file
config = None
with open("config.json", "r") as config_file:
    config = ujson.load(config_file)

class Sumorobot(object):

    # ultrasonic distance sensor
    echo = Pin(14, Pin.IN)
    trigger = Pin(27, Pin.OUT)

    # Servo PWM-s
    pwm_left = PWM(Pin(15), freq=50, duty=0)
    pwm_right = PWM(Pin(4), freq=50, duty=0)

    # bottom LED
    bottom_led = Pin(5, Pin.OUT)
    # bottom LED is in reverse polarity
    bottom_led.value(1)
    # sensor LEDs
    opponent_led = Pin(16, Pin.OUT)
    left_line_led = Pin(17, Pin.OUT)
    right_line_led = Pin(12, Pin.OUT)

    # battery gauge
    adc_battery = ADC(Pin(32))

    # the phototransistors
    adc_line_left = ADC(Pin(34))
    adc_line_right = ADC(Pin(33))

    # Set reference voltage to 3.3V
    adc_battery.atten(ADC.ATTN_11DB)
    adc_line_left.atten(ADC.ATTN_11DB)
    adc_line_right.atten(ADC.ATTN_11DB)

    # for highlighting blockly blocks
    highlight_block = None

    # for terminating sleep
    terminate = False

    # to smooth out ultrasonic sensor value
    opponent_score = 0

    def __init__(self, highlight_block):
        self.highlight_block = highlight_block

    def set_led(self, led, state):
        # set the given LED state
        if led == STATUS:
            self.bottom_led.value(0 if state else 1)
        elif led == OPPONENT:
            self.opponent_led.value(state)
        elif led == LEFT_LINE:
            self.left_line_led.value(state)
        elif led == RIGHT_LINE:
            self.right_line_led.value(state)

    def get_battery_voltage(self):
        return round(config["battery_coeff"] * (self.adc_battery.read() * 3.3 / 4096), 2)

    def get_opponent_distance(self):
        # send a pulse
        self.trigger.value(0)
        sleep_us(5)
        self.trigger.value(1)
        sleep_us(10)
        self.trigger.value(0)
        # wait for the pulse and calculate the distance
        return (time_pulse_us(self.echo, 1, 30000) / 2) / 29.1

    def is_opponent(self, block_id = None):
        # if block_id given and blockly highlight is on
        if block_id and config["blockly_highlight"]:
            self.highlight_block(block_id)

        # get the opponent distance
        self.opponent_distance = self.get_opponent_distance()
        # if the opponent is close and the ping actually returned
        if self.opponent_distance < config["ultrasonic_distance"] and self.opponent_distance > 0:
            # if not maximum score
            if self.opponent_score < 5:
                # increase the opponent score
                self.opponent_score += 1
        # if no opponent was detected
        else:
            # if not lowest score
            if self.opponent_score > 0:
                # decrease the opponent score
                self.opponent_score -= 1

        # if the sensor saw something more than 2 times
        opponent = True if self.opponent_score > 2 else False

        # trigger opponent LED
        self.set_led(OPPONENT, opponent)

        return opponent

    def calibrate_line(self):
        # read the line sensor values
        config["left_line_threshold"] = self.adc_line_left.read()
        config["right_line_threshold"] = self.adc_line_right.read()
        # update the config file
        with open("config.part", "w") as config_file:
            config_file.write(ujson.dumps(config))
        os.rename("config.part", "config.json")

    def get_line(self, dir):
        # check for valid direction
        assert dir == LEFT or dir == RIGHT

        # return the given line sensor value
        if dir == LEFT:
            return self.adc_line_left.read()
        elif dir == RIGHT:
            return self.adc_line_right.read()

    def is_line(self, dir, block_id = None):
        # check for valid direction
        assert dir == LEFT or dir == RIGHT

        # if block_id given and blockly highlight is on
        if block_id and config["blockly_highlight"]:
            self.highlight_block(block_id)

        # return the given line sensor value
        if dir == LEFT:
            line = abs(self.adc_line_left.read() - config["left_line_threshold"]) > 1000
            self.set_led(LEFT_LINE, line)
            return line
        elif dir == RIGHT:
            line = abs(self.adc_line_right.read() - config["right_line_threshold"]) > 1000
            self.set_led(RIGHT_LINE, line)
            return line

    def detach_servos(self):
        self.set_servo(LEFT, 0)
        self.set_servo(RIGHT, 0)

    prev_speed = {LEFT: 0, RIGHT: 0}
    def set_servo(self, dir, speed):
        # check for valid direction
        assert dir == LEFT or dir == RIGHT
        # check for valid speed
        assert speed <= 100 and speed >= -100

        # when the speed didn't change
        if speed == self.prev_speed[dir]:
            return

        # record the new speed
        self.prev_speed[dir] = speed

        # set the given servo speed
        if dir == LEFT:
            if speed == 0:
                self.pwm_left.duty(0)
            else:
                self.pwm_left.duty(int(33 + config["left_servo_tuning"] + speed * 33 / 100)) # -100 ... 100 to 33 .. 102
        elif dir == RIGHT:
            if speed == 0:
                self.pwm_right.duty(0)
            else:
                self.pwm_right.duty(int(33 + config["right_servo_tuning"] + speed * 33 / 100)) # -100 ... 100 to 33 .. 102

    def move(self, dir, block_id = None):
        # check for valid direction
        assert dir == STOP or dir == RIGHT or dir == LEFT or dir == BACKWARD or dir == FORWARD

        # if block_id given and blockly highlight is on
        if block_id and config["blockly_highlight"]:
            self.highlight_block(block_id)

        # go to the given direction
        if dir == STOP:
            self.set_servo(LEFT, 0)
            self.set_servo(RIGHT, 0)
        elif dir == LEFT:
            self.set_servo(LEFT, -100)
            self.set_servo(RIGHT, -100)
        elif dir == RIGHT:
            self.set_servo(LEFT, 100)
            self.set_servo(RIGHT, 100)
        elif dir == FORWARD:
            self.set_servo(LEFT, 100)
            self.set_servo(RIGHT, -100)
        elif dir == BACKWARD:
            self.set_servo(LEFT, -100)
            self.set_servo(RIGHT, 100)

    def sleep(self, delay, block_id = None):
        # check for valid delay
        assert delay > 0

        # if block_id given and blockly highlight is on
        if block_id and config["blockly_highlight"]:
            self.highlight_block(block_id)

        # split the delay into 50ms chunks
        for j in range(0, delay, 50):
            # check for forceful termination
            if self.terminate:
                # terminate the delay
                return
            else:
                sleep_ms(50)
