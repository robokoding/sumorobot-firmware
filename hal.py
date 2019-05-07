import os
import ujson
from utime import sleep_us, sleep_ms
from machine import Pin, PWM, ADC, time_pulse_us

# LEDs
STATUS = 0
OPPONENT = 1
LEFT_LINE = 2
RIGHT_LINE = 3

# Directions
STOP = 0
LEFT = 1
RIGHT = 2
SEARCH = 3
FORWARD = 4
BACKWARD = 5

class Sumorobot(object):
    # Constructor
    def __init__(self, config = None):
        # Config file
        self.config = config

        # Ultrasonic distance sensor
        self.echo = Pin(14, Pin.IN)
        self.trigger = Pin(27, Pin.OUT)

        # Servo PWM-s
        self.pwm_left = PWM(Pin(15), freq=50, duty=0)
        self.pwm_right = PWM(Pin(4), freq=50, duty=0)

        # LED sensor feedback
        self.sensor_feedback = True
        # Bottom status LED
        self.status_led = Pin(self.config["status_led_pin"], Pin.OUT)
        # Bottom status LED is in reverse polarity
        self.status_led.value(1)
        # Sensor LEDs
        self.opponent_led = Pin(16, Pin.OUT)
        self.left_line_led = Pin(17, Pin.OUT)
        self.right_line_led = Pin(12, Pin.OUT)

        # Scope with sensor data
        self.sensor_scope = dict()

        # WiFi connection
        self.is_wifi_connected = False

        # Python and Blockly code
        self.python_code = ""
        self.blockly_code = ""
        self.compiled_python_code = ""

        # Battery gauge
        self.bat_status = 4.3
        self.move_counter = 0
        self.adc_battery = ADC(Pin(32))
        self.bat_charge = Pin(25, Pin.IN)

        # The pullups for the phototransistors
        Pin(19, Pin.IN, Pin.PULL_UP)
        Pin(23, Pin.IN, Pin.PULL_UP)

        # The phototransistors
        self.last_line = LEFT
        self.adc_line_left = ADC(Pin(34))
        self.adc_line_right = ADC(Pin(33))

        # Set reference voltage to 3.3V
        self.adc_battery.atten(ADC.ATTN_11DB)
        self.adc_line_left.atten(ADC.ATTN_11DB)
        self.adc_line_right.atten(ADC.ATTN_11DB)

        # To smooth out ultrasonic sensor value
        self.opponent_score = 0

        # For terminating sleep
        self.terminate = False

        # For search mode
        self.search = False
        self.search_counter = 0

        # Memorise previous servo speeds
        self.prev_speed = {LEFT: 0, RIGHT: 0}

    # Function to set LED states
    def set_led(self, led, state):
        # Set the given LED state
        if led == STATUS:
            # Status LED is reverse polarity
            self.status_led.value(0 if state else 1)
        elif led == OPPONENT:
            self.opponent_led.value(state)
        elif led == LEFT_LINE:
            self.left_line_led.value(state)
        elif led == RIGHT_LINE:
            self.right_line_led.value(state)

    # Function to shortly bink status LED
    def toggle_led(self, timer = None):
        self.status_led.value(0)
        sleep_ms(10)
        self.status_led.value(1)

    # Function to get battery voltage
    def get_battery_voltage(self):
        bat = round(self.config["battery_coeff"] * (self.adc_battery.read() * 3.3 / 4096), 2)
        # When the SumoRobot is not moving
        if self.prev_speed[LEFT] == 0 and self.prev_speed[RIGHT] == 0:
            if self.move_counter > 0:
                self.move_counter -= 1
            if self.bat_status < bat - 0.20 and self.move_counter == 0:
                #deepsleep()
                pass
            self.bat_status = bat
        else:
            self.move_counter = 10
        return bat

    # Function to get distance (cm) from the object in front of the SumoRobot
    def get_opponent_distance(self):
        # Send a pulse
        self.trigger.value(0)
        sleep_us(5)
        self.trigger.value(1)
        sleep_us(10)
        self.trigger.value(0)
        # Wait for the pulse and calculate the distance
        return round((time_pulse_us(self.echo, 1, 30000) / 2) / 29.1, 2)

    # Function to get boolean if there is something in front of the SumoRobot
    def is_opponent(self):
        # Get the opponent distance
        self.opponent_distance = self.get_opponent_distance()
        # When the opponent is close and the ping actually returned
        if self.opponent_distance < self.config["ultrasonic_distance"] and self.opponent_distance > 0:
            # When not maximum score
            if self.opponent_score < 5:
                # Increase the opponent score
                self.opponent_score += 1
        # When no opponent was detected
        else:
            # When not lowest score
            if self.opponent_score > 0:
                # Decrease the opponent score
                self.opponent_score -= 1

        # When the sensor saw something more than 2 times
        opponent = True if self.opponent_score > 2 else False

        # Trigger opponent LED
        self.set_led(OPPONENT, opponent)

        return opponent

    # Function to update line calibration and write it to the config file
    def calibrate_line_value(self):
        # Read the line sensor values
        self.config["left_line_value"] = self.adc_line_left.read()
        self.config["right_line_value"] = self.adc_line_right.read()
        # Update the config file
        with open("config.part", "w") as config_file:
            config_file.write(ujson.dumps(self.config))
        os.rename("config.part", "config.json")

    # Function to update line threshold calibration and write it to the config file
    def set_line_threshold(self, value):
        # Read the line sensor values
        self.config["left_line_threshold"] = value
        self.config["right_line_threshold"] = value
        # Update the config file
        with open("config.part", "w") as config_file:
            config_file.write(ujson.dumps(self.config))
        os.rename("config.part", "config.json")

    # Function to get light inensity from the phototransistors
    def get_line(self, dir):
        # Check if the direction is valid
        assert dir in (LEFT, RIGHT)

        # Return the given line sensor value
        if dir == LEFT:
            return self.adc_line_left.read()
        elif dir == RIGHT:
            return self.adc_line_right.read()

    def is_line(self, dir):
        # Check if the direction is valid
        assert dir in (LEFT, RIGHT)

        # Return the given line sensor value
        if dir == LEFT:
            line = abs(self.get_line(LEFT) - self.config["left_line_value"]) > self.config["left_line_threshold"]
            self.set_led(LEFT_LINE, line)
            last_line = LEFT
            return line
        elif dir == RIGHT:
            line = abs(self.get_line(RIGHT) - self.config["right_line_value"]) > self.config["right_line_threshold"]
            self.set_led(RIGHT_LINE, line)
            last_line = RIGHT
            return line

    def set_servo(self, dir, speed):
        # Check if the direction is valid
        assert dir in (LEFT, RIGHT)
        # Check if the speed is valid
        assert speed <= 100 and speed >= -100

        # When the speed didn't change
        if speed == self.prev_speed[dir]:
            return

        # Record the new speed
        self.prev_speed[dir] = speed

        # Set the given servo speed
        if dir == LEFT:
            if speed == 0:
                self.pwm_left.duty(0)
            else:
                # -100 ... 100 to 33 .. 102
                self.pwm_left.duty(int(33 + self.config["left_servo_tuning"] + speed * 33 / 100))
        elif dir == RIGHT:
            if speed == 0:
                self.pwm_right.duty(0)
            else:
                # -100 ... 100 to 33 .. 102
                self.pwm_right.duty(int(33 + self.config["right_servo_tuning"] + speed * 33 / 100))

    def move(self, dir):
        # Check if the direction is valid
        assert dir in (SEARCH, STOP, RIGHT, LEFT, BACKWARD, FORWARD)

        # Go to the given direction
        if dir == STOP:
            self.set_servo(LEFT, 0)
            self.set_servo(RIGHT, 0)
        elif dir == LEFT:
            self.set_servo(LEFT, -100)
            self.set_servo(RIGHT, -100)
        elif dir == RIGHT:
            self.set_servo(LEFT, 100)
            self.set_servo(RIGHT, 100)
        elif dir == SEARCH:
            # Change search mode after X seconds
            if self.search_counter == 50:
                self.search = not self.search
                self.search_counter = 0
            # When in search mode
            if self.search:
                # Go forward
                self.set_servo(LEFT, 100)
                self.set_servo(RIGHT, -100)
            elif last_line == RIGHT:
                # Go left
                self.set_servo(LEFT, -100)
                self.set_servo(RIGHT, -100)
            else:
                # Go right
                self.set_servo(LEFT, 100)
                self.set_servo(RIGHT, 100)
            # Increase search counter
            self.search_counter += 1
        elif dir == FORWARD:
            self.set_servo(LEFT, 100)
            self.set_servo(RIGHT, -100)
        elif dir == BACKWARD:
            self.set_servo(LEFT, -100)
            self.set_servo(RIGHT, 100)

    def update_sensor_feedback(self):
        if self.sensor_feedback:
            # Execute to see LED feedback for sensors
            self.is_opponent()
            self.is_line(LEFT)
            self.is_line(RIGHT)

    def update_sensor_scope(self):
        self.sensor_scope = dict(
            left_line = self.get_line(LEFT),
            right_line = self.get_line(RIGHT),
            opponent = self.get_opponent_distance(),
            battery_charge = self.bat_charge.value(),
            battery_voltage = self.get_battery_voltage()
        )

    def get_python_code(self):
        return dict(
            type = "python_code",
            val = self.python_code
        )

    def get_blockly_code(self):
        return dict(
            type = "blockly_code",
            val = self.blockly_code
        )

    def get_sensor_scope(self):
        temp = self.sensor_scope
        temp['type'] = "sensor_scope"
        return temp

    def get_line_scope(self):
        return dict(
            type = "line_scope",
            left_line_value = self.config["left_line_value"],
            right_line_value = self.config["right_line_value"],
            left_line_threshold = self.config["left_line_threshold"],
            right_line_threshold = self.config["right_line_threshold"]
        )

    def sleep(self, delay):
        # Check for valid delay
        assert delay > 0

        # Split the delay into 50ms chunks
        for j in range(0, delay, 50):
            # Check for forceful termination
            if self.terminate:
                # Terminate the delay
                return
            else:
                sleep_ms(50)
