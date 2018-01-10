import _thread
import ubinascii
from utime import sleep_ms
from machine import Pin, PWM, Timer, UART

conn = None
conn_highlight = None
name = "sumo-%s" % ubinascii.hexlify(wlan.config("mac")[-3:]).decode("ascii")

# remote server
url = "ws://iot.koodur.com:80/p2p/" + name + "/browser/"
url_highlight = "ws://iot.koodur.com:80/p2p/" + name + "-highlight/browser/"

# local server
#url = "ws://10.42.0.1:80/p2p/" + name + "/browser/"
#url_highlight = "ws://10.42.0.1:80/p2p/" + name + "-highlight/browser/"

scope = dict()
# send blocks IDs for highlighting
no_delay = False
highlight = True
ast = "move(STOP, '')"

def is_enemy(block_id):
    if block_id != "" and highlight:
        conn_highlight.send(block_id)
    return enemy_distance()

def is_line(dir, block_id):
    if block_id != "" and highlight:
        conn_highlight.send(block_id)
    if dir == LEFT:
        return line_left()
    elif dir == RIGHT:
        return line_right()
    return False

def move(dir, block_id):
    if block_id != "" and highlight:
        conn_highlight.send(block_id)
    if dir == STOP:
        motor_left(0)
        motor_right(0)
    elif dir == LEFT:
        motor_left(-100)
        motor_right(-100)
    elif dir == RIGHT:
        motor_left(100)
        motor_right(100)
    elif dir == FORWARD:
        motor_left(100)
        motor_right(-100)
    elif dir == BACKWARD:
        motor_left(-100)
        motor_right(100)

def move2(dir, block_id):
    if block_id != "" and highlight:
        conn_highlight.send(block_id)
    if dir == STOP:
        motor_left(0)
        motor_right(0)
    elif dir == RIGHT:
        motor_left(-100)
        motor_right(-100)
    elif dir == LEFT:
        motor_left(100)
        motor_right(100)
    elif dir == BACKWARD:
        motor_left(100)
        motor_right(-100)
    elif dir == FORWARD:
        motor_left(-100)
        motor_right(100)

def sleep_wrapper(delay, block_id):
    if block_id != "" and highlight:
        conn_highlight.send(block_id)
    for j in range(0, delay, 10):
        if ast == "move(STOP, '')":
            return # TODO: raise exception
        else:
            sleep_ms(10)

exported_functions = dict(
    STOP = STOP,
    LEFT = LEFT,
    RIGHT = RIGHT,
    FORWARD = FORWARD,
    BACKWARD = BACKWARD,
    move = move,
    is_line = is_line,
    is_enemy = is_enemy,
    sleep = sleep_wrapper,
    motor_left = motor_left,
    motor_right = motor_right
)

exported_functions2 = dict(
    STOP = STOP,
    LEFT = LEFT,
    RIGHT = RIGHT,
    FORWARD = FORWARD,
    BACKWARD = BACKWARD,
    move = move2,
    is_line = is_line,
    is_enemy = is_enemy,
    sleep = sleep_wrapper,
    motor_left = motor_left,
    motor_right = motor_right
)

def step():
    global scope

    shuffle = False
    while True:
        scope = dict(
            enemy = is_enemy(""),
            line_left = is_line(LEFT, ""),
            line_right = is_line(RIGHT, ""),
            battery_voltage = get_battery_voltage(),
        )
        if no_delay:
            if shuffle:
                current = exported_functions.copy()
            else:
                current = exported_functions2.copy()
            shuffle = not shuffle
        else:
            current = exported_functions.copy()
        current.update(scope)
        exec(ast, current)
        # leave time to process WebSocket commands
        sleep_ms(50)

def ws_handler():
    global ast
    global conn
    global scope
    global no_delay

    uart = UART(2, baudrate=115200, rx=34, tx=35, timeout=1)
    uart.write("uart works, yee!\n")
    while True:
        try:
            fin, opcode, data = conn.read_frame()
            cmd = uart.readline()
        except: # urror
            print("Exception while reading from socket, attempting reconnect")
            conn = uwebsockets.connect(url)
            continue

        if cmd:
            print("command:", cmd)

        if data == b"forward":
            #print("Going forward")
            ast = "move(FORWARD, '')"
        elif data == b"backward":
            #print("Going backward")
            ast = "move(BACKWARD, '')"
        elif data == b"right":
            #print("Going right")
            ast = "move(RIGHT, '')"
        elif data == b"left":
            #print("Going left")
            ast = "move(LEFT, '')"
        elif data == b"kick":
            conn.send(repr(scope))
        elif data == b"ping":
            conn.send(repr(scope))
        elif data.startswith("start:"):
            print("Got code:")#, data[6:])
            if b"sleep" in data or b"if" in data or len(data.splitlines()) == 1:
                no_delay = False
            else:
                no_delay = True
            ast = compile(data[6:], "snippet", "exec")
        elif data == b"stop":
            ast = "move(STOP, '')"
            print("Got stop")
        elif b"Gone" in data:
            print("Server said 410 Gone, attempting to reconnect...")
            conn = uwebsockets.connect(url)
        else:
            print("unknown command:", data)

# wait for WiFi to get connected
while not wlan.isconnected():
    sleep_ms(100)

# connect to the websocket
print("Connecting to:", url)
conn = uwebsockets.connect(url)

# send a ping to the robot
print("Sending ping")
conn.send("{'ping': true}")
conn.send("{'ip': '" + wlan.ifconfig()[0] + "'}")

# connect to the block highlight websocket
conn_highlight = uwebsockets.connect(url_highlight)

# indicate that the WebSocket is connected
set_led(STATUS, True)

print("Starting WebSocket and code loop")
# start the code processing thread
_thread.start_new_thread(step, ())
# start the Websocket processing thread
_thread.start_new_thread(ws_handler, ())
