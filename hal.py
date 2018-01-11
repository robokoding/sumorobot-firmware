from utime import sleep_us, sleep_ms
from machine import Pin, PWM, ADC, time_pulse_us

# LEDs
ENEMY = 0
STATUS = 1
LEFT_LINE = 2
RIGHT_LINE = 3

# directions
STOP = 0
LEFT = 1
RIGHT = 2
FORWARD = 3
BACKWARD = 4

# blockl highlight
BLOCK_HIGHLIGHT = True

# Battery resistor ladder ratio
BATTERY_COEFF = 2.25

# Ultrasonic sensor calibration
ULTRASONIC_OFFSET = 800

# Servo timing
MOTOR_LEFT_TUNING = 33
MOTOR_RIGHT_TUNING = 33

# Calibrate line sensors
LINE_LEFT_THRESHOLD = 1000
LINE_RIGHT_THRESHOLD = 1000

class Sumorobot(object):

    # Ultrasonic distance sensor
    echo = Pin(14, Pin.IN)
    trigger = Pin(27, Pin.OUT)

    # Motor PWM-s
    pwm_left = PWM(Pin(15), freq=50, duty=0)
    pwm_right = PWM(Pin(4), freq=50, duty=0)

    # bottom LED
    bottom_led = Pin(5, Pin.OUT)
    # bottom LED is in reverse polarity
    bottom_led.value(1)
    # sensor LEDs
    enemy_led = Pin(16, Pin.OUT)
    left_line_led = Pin(17, Pin.OUT)
    right_line_led = Pin(12, Pin.OUT)

    # Battery gauge
    adc_battery = ADC(Pin(32))

    # Optek sensors
    adc_line_left = ADC(Pin(34))
    adc_line_right = ADC(Pin(33))

    # Set reference voltage to 3.3V
    adc_battery.atten(ADC.ATTN_11DB)
    adc_line_left.atten(ADC.ATTN_11DB)
    adc_line_right.atten(ADC.ATTN_11DB)

    # for highlighting blocks
    highlight_block = None

    # for terminating sleep
    terminate = False

    def __init__(self, highlight_block):
        self.highlight_block = highlight_block

    def set_led(self, led, state):
        if led == STATUS:
            self.bottom_led.value(0 if state else 1)
        elif led == ENEMY:
            self.enemy_led.value(state)
        elif led == LEFT_LINE:
            self.left_line_led.value(state)
        elif led == RIGHT_LINE:
            self.right_line_led.value(state)

    def get_battery_voltage(self):
        return round(BATTERY_COEFF * (self.adc_battery.read() * 3.3 / 4096), 2)

    def get_enemy_distance(self):
        # send a pulse
        self.trigger.value(0)
        sleep_us(5)
        self.trigger.value(1)
        sleep_us(10)
        self.trigger.value(0)
        # wait for the pulse and calculate the distance
        return (time_pulse_us(self.echo, 1, 30000) / 2) / 29.1

    enemy_score = 0
    def is_enemy(self, block_id = None):
        if block_id and BLOCK_HIGHLIGHT:
            self.highlight_block(block_id)

        # get the enemy distance
        self.enemy_distance = self.get_enemy_distance()
        # if the enemy is close and the ping actually returned
        if self.enemy_distance < 60 and self.enemy_distance > 0:
            # if not maximum score
            if self.enemy_score < 5:
                # increase the enemy score
                self.enemy_score += 1
        # if no enemy was detected
        else:
            # if not lowest score
            if self.enemy_score > 0:
                # decrease the enemy score
                self.enemy_score -= 1

        # if the sensor saw something more than 2 times
        enemy = True if self.enemy_score > 2 else False

        # trigger enemy LED
        self.set_led(ENEMY, enemy)

        return enemy

    def get_line(self, dir):
        # check for valid direction
        assert dir == LEFT or dir == RIGHT

        if dir == LEFT:
            return self.adc_line_left.read()
        elif dir == RIGHT:
            return self.adc_line_right.read()

    def is_line(self, dir, block_id = None):
        # check for valid direction
        assert dir == LEFT or dir == RIGHT

        # if block_id given and BLOCK_HIGHLIGHT
        if block_id and BLOCK_HIGHLIGHT:
            self.highlight_block(block_id)

        if dir == LEFT:
            line = abs(self.adc_line_left.read() - LINE_LEFT_THRESHOLD) > 1000
            self.set_led(LEFT_LINE, line)
            return line
        elif dir == RIGHT:
            line = abs(self.adc_line_right.read() - LINE_RIGHT_THRESHOLD) > 1000
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

        if dir == LEFT:
            if speed == 0:
                self.pwm_left.duty(0)
            else:
                self.pwm_left.duty(int(33 + MOTOR_LEFT_TUNING + speed * 33 / 100)) # -100 ... 100 to 33 .. 102
        elif dir == RIGHT:
            if speed == 0:
                self.pwm_right.duty(0)
            else:
                self.pwm_right.duty(int(33 + MOTOR_RIGHT_TUNING + speed * 33 / 100)) # -100 ... 100 to 33 .. 102


    def move(self, dir, block_id = None):
        # check for valid direction
        assert dir == STOP or dir == RIGHT or dir == LEFT or dir == BACKWARD or dir == FORWARD

        # if block_id given and BLOCK_HIGHLIGHT
        if block_id and BLOCK_HIGHLIGHT:
            self.highlight_block(block_id)

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

        # if block_id given and BLOCK_HIGHLIGHT
        if block_id and BLOCK_HIGHLIGHT:
            self.highlight_block(block_id)

        for j in range(0, delay, 50):
            if self.terminate:
                return # TODO: raise exception
            else:
                sleep_ms(50)
