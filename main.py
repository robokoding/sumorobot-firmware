import _thread
import ubinascii
import uwebsockets

# Extract a unique name for the robot from the device MAC address
mac = ubinascii.hexlify(wlan.config("mac")[-3:]).decode("ascii")

# SumoRobot server
server_url = config["sumo_server"]

# Code to execute
ast = ""
# Scope, info to be sent to the client
scope = dict()

def step():
    global scope

    while True:
        # Execute to see LED feedback for sensors
        sumorobot.is_opponent()
        sumorobot.is_line(LEFT)
        sumorobot.is_line(RIGHT)
        # Update scope
        scope = dict(
            to = "browser-%s@00000514" % mac,
            line_left = sumorobot.get_line(LEFT),
            line_right = sumorobot.get_line(RIGHT),
            opponent = sumorobot.get_opponent_distance(),
            battery_voltage = sumorobot.get_battery_voltage(),
        )
        # Execute code
        exec(ast)
        # When robot was stopped
        if sumorobot.terminate:
            # Disable forceful termination of delays in code
            sumorobot.terminate = False
            # Stop the robot
            sumorobot.move(STOP)
        # Leave time to process WebSocket commands
        sleep_ms(50)

def ws_handler():
    global ast
    global has_wifi_connection

    while True:
        # When WiFi has just been reconnected
        if wlan.isconnected() and not has_wifi_connection:
            #conn = uwebsockets.connect(url)
            sumorobot.set_led(STATUS, True)
            has_wifi_connection = True
        # When WiFi has just been disconnected
        elif not wlan.isconnected() and has_wifi_connection:
            sumorobot.set_led(STATUS, False)
            has_wifi_connection = False
        elif not wlan.isconnected():
            # Continue to wait for a WiFi connection
            continue

        try: # Try to read from the WebSocket
            data = conn.recv()
        except: # Socket timeout, no data received
            # Continue to try to read data
            continue

        # When an empty frame was received
        if not data:
            # Continue to receive data
            continue
        elif b'forward' in data:
            ast = ""
            sumorobot.move(FORWARD)
        elif b'backward' in data:
            ast = ""
            sumorobot.move(BACKWARD)
        elif b'right' in data:
            ast = ""
            sumorobot.move(RIGHT)
        elif b'left' in data:
            ast = ""
            sumorobot.move(LEFT)
        elif b'ping' in data:
            conn.send(repr(scope).replace("'", '"'))
        elif b'code' in data:
            data = ujson.loads(data)
            data['val'] = data['val'].replace(";;", "\n")
            print("code:", data['val'])
            ast = compile(data['val'], "snippet", "exec")
        elif b'stop' in data:
            ast = ""
            sumorobot.move(STOP)
            # for terminating delays in code
            sumorobot.terminate = True
        elif b'calibrate_line' in data:
            sumorobot.calibrate_line()
        elif b'Gone' in data:
            print("server said 410 Gone, attempting to reconnect...")
            #conn = uwebsockets.connect(url)
        else:
            print("unknown cmd:", data)

# Wait for WiFi to get connected
while not wlan.isconnected():
    sleep_ms(100)

# Connect to the websocket
conn = uwebsockets.connect(url)

# Set X seconds timeout for socket reads
conn.settimeout(1)

# Send a ping to the robot
conn.send('{"setID": "sumo-%s@00000514", "passwd": "salakala"}' % mac)
# Receive session and auth ok frames
conn.recv()
conn.recv()

# Stop bootup blinking
timer.deinit()

# WiFi is connected
has_wifi_connection = True
# Indicate that the WebSocket is connected
sumorobot.set_led(STATUS, True)

# Start the code processing thread
_thread.start_new_thread(step, ())
# Start the Websocket processing thread
_thread.start_new_thread(ws_handler, ())
