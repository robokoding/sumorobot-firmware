from utime import sleep_us, sleep_ms
from machine import Pin, PWM, ADC, time_pulse_us

# LEDs
STATUS = 0
SONAR = 1
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

        # Sonar distance sensor
        self.echo = Pin(14, Pin.IN)
        self.trigger = Pin(27, Pin.OUT)

        # Servo PWM-s
        self.pwm = {
            LEFT: PWM(Pin(15), freq=50, duty=0),
            RIGHT: PWM(Pin(4), freq=50, duty=0)
        }

        # LED sensor feedback
        self.sensor_feedback = True
        # Bottom status LED
        self.status_led = Pin(self.config['status_led_pin'], Pin.OUT)
        # Bottom status LED is in reverse polarity
        self.status_led.value(1)
        # Sensor LEDs
        self.sonar_led = Pin(16, Pin.OUT)
        self.left_line_led = Pin(17, Pin.OUT)
        self.right_line_led = Pin(12, Pin.OUT)

        # Battery level in %
        self.battery_level = 0

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

        # To smooth out sonar sensor value
        self.sonar_score = 0

        # For terminating sleep
        self.terminate = False

        # For search mode
        self.search = False
        self.search_counter = 0

        # Memorise previous servo speeds
        self.prev_speed = {LEFT: 0, RIGHT: 0}

    # Function to set LED states
    def set_led(self, led, value):
        # Turn the given LED on or off
        if led == STATUS:
            # Status LED is reverse polarity
            self.status_led.value(0 if value else 1)
        elif led == SONAR:
            self.sonar_led.value(value)
        elif led == LEFT_LINE:
            self.left_line_led.value(value)
        elif led == RIGHT_LINE:
            self.right_line_led.value(value)

    # Function to get battery level in percentage
    def get_battery_level(self):
        # When the SumoRobot is not moving
        if self.prev_speed[LEFT] == 0 and self.prev_speed[RIGHT] == 0:
            # Calculate battery voltage
            battery_voltage = round(self.config['battery_coeff'] * (self.adc_battery.read() * 3.3 / 4096), 2)
            # Map battery voltage to percentage
            temp_battery_level = 0.0 + ((100.0 - 0.0) / (4.2 - 3.2)) * (battery_voltage - 3.2)
            # When battery level changed more than 5 percent
            if abs(self.battery_level - temp_battery_level) > 5:
                # Update battery level
                self.battery_level = round(temp_battery_level)
        # Return the battery level in percentage
        return min(100, max(0, self.battery_level))

    # Function to get distance (cm) from the object in front of the SumoRobot
    def get_sonar_value(self):
        # Send a pulse
        self.trigger.value(0)
        sleep_us(5)
        self.trigger.value(1)
        sleep_us(10)
        self.trigger.value(0)
        # Wait for the pulse and calculate the distance
        return round((time_pulse_us(self.echo, 1, 30000) / 2) / 29.1)

    # Function to get boolean if there is something in front of the SumoRobot
    def is_sonar(self):
        # Get the sonar value
        self.sonar_value = self.get_sonar_value()
        # When the sonar value is small and the ping actually returned
        if self.sonar_value < self.config['sonar_threshold'] and self.sonar_value > 0:
            # When not maximum score
            if self.sonar_score < 5:
                # Increase the sonar score
                self.sonar_score += 1
        # When no sonar ping was returned
        else:
            # When not lowest score
            if self.sonar_score > 0:
                # Decrease the sonar score
                self.sonar_score -= 1

        # When the sensor saw something more than 2 times
        value = True if self.sonar_score > 2 else False

        # Trigger sonar LED
        self.set_led(SONAR, value)

        return value

    # Function to update the config file
    def update_config_file(self):
        # Update the config file
        with open('config.part', 'w') as config_file:
            config_file.write(ujson.dumps(self.config))
        os.rename('config.part', 'config.json')

    # Function to update line calibration and write it to the config file
    def calibrate_line_values(self):
        # Read the line sensor values
        self.config['left_line_value'] = self.adc_line_left.read()
        self.config['right_line_value'] = self.adc_line_right.read()

    # Function to get light inensity from the phototransistors
    def get_line(self, line):
        # Check if the direction is valid
        assert line in (LEFT, RIGHT)

        # Return the given line sensor value
        if line == LEFT:
            return self.adc_line_left.read()
        elif line == RIGHT:
            return self.adc_line_right.read()

    def is_line(self, line):
        # Check if the direction is valid
        assert line in (LEFT, RIGHT)

        # Define feedback LED
        led = LEFT_LINE if line == LEFT else RIGHT_LINE
        # Define config prefix
        prefix = 'left' if line == LEFT else 'right'
        # Check for line
        value = abs(self.get_line(line) - self.config[prefix + '_line_value']) > self.config[prefix + '_line_threshold']
        # Show LED feedback
        self.set_led(led, value)
        # Update last line direction if line was detected
        self.last_line = value if value else self.last_line
        # Return the given line sensor value
        return value

    def set_servo(self, servo, speed):
        # Check if the direction is valid
        assert servo in (LEFT, RIGHT)
        # Check if the speed is valid
        assert speed <= 100 and speed >= -100

        # When the speed didn't change
        if speed == self.prev_speed[servo]:
            return

        # Save the new speed
        self.prev_speed[servo] = speed

        # Set the given servo speed
        if speed == 0:
            self.pwm[servo].duty(0)
        else:
            # Define config prefix
            prefix = 'left' if servo == LEFT else 'right'
            # -100 ... 100 to min_tuning .. max_tuning
            min_tuning = self.config[prefix + '_servo_min_tuning']
            max_tuning = self.config[prefix + '_servo_max_tuning']
            self.pwm[servo].duty(int((speed + 100) / 200 * (max_tuning - min_tuning) + min_tuning))

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
                self.move(FORWARD)
            elif self.last_line == RIGHT:
                self.move(LEFT)
            else:
                self.move(RIGHT)
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
            self.is_sonar()
            self.is_line(LEFT)
            self.is_line(RIGHT)

    def get_sensor_scope(self):
        # TODO: implement sensor value caching
        return str(self.get_sonar_value()) + ',' \
            + str(self.get_line(LEFT)) + ',' \
            + str(self.get_line(RIGHT)) + ',' \
            + str(self.bat_charge.value()) + ',' \
            + str(self.get_battery_level())

    def get_configuration_scope(self):
        return str(self.config['sumorobot_name']) + ',' \
            + str(self.config['firmware_version']) + ',' \
            + str(self.config['left_line_value']) + ',' \
            + str(self.config['right_line_value']) + ',' \
            + str(self.config['left_line_threshold']) + ',' \
            + str(self.config['right_line_threshold']) + ',' \
            + str(self.config['sonar_threshold'])

    def sleep(self, delay):
        # Check for valid delay
        assert delay > 0

        # Split the delay into 50ms chunks
        while delay:
            # Check for forceful termination
            if self.terminate:
                # Terminate the delay
                return
            else:
                sleep_ms(50)

            delay -= 50
