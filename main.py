import _thread
import ubinascii
import uwebsockets

def step():
    while True:
        # Execute to see LED feedback for sensors
        sumorobot.update_sensor_feedback()
        # Update sensor scope
        sumorobot.update_sensor_scope()
        # Try to execute the Python code
        try:
            exec(sumorobot.compiled_python_code)
        except:
            pass
        # When robot was stopped
        if sumorobot.terminate:
            # Disable forceful termination of delays in code
            sumorobot.terminate = False
            # Stop the robot
            sumorobot.move(STOP)
        # Leave time to process WebSocket commands
        sleep_ms(50)

def ws_handler():
    while True:
        # When WiFi has just been reconnected
        if wlan.isconnected() and not sumorobot.is_wifi_connected:
            #conn = uwebsockets.connect(url)
            sumorobot.set_led(STATUS, True)
            sumorobot.is_wifi_connected = True
        # When WiFi has just been disconnected
        elif not wlan.isconnected() and sumorobot.is_wifi_connected:
            sumorobot.set_led(STATUS, False)
            sumorobot.is_wifi_connected = False
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
            sumorobot.compiled_python_code = ""
            sumorobot.move(FORWARD)
        elif b'backward' in data:
            sumorobot.compiled_python_code = ""
            sumorobot.move(BACKWARD)
        elif b'right' in data:
            sumorobot.compiled_python_code = ""
            sumorobot.move(RIGHT)
        elif b'left' in data:
            sumorobot.compiled_python_code = ""
            sumorobot.move(LEFT)
        elif b'stop' in data:
            sumorobot.compiled_python_code = ""
            sumorobot.move(STOP)
            # for terminating delays in code
            sumorobot.terminate = True
        elif b'get_line_scope' in data:
            conn.send(ujson.dumps(sumorobot.get_line_scope()))
        elif b'get_sensor_scope' in data:
            conn.send(ujson.dumps(sumorobot.get_sensor_scope()))
        elif b'get_python_code' in data:
            print(sumorobot.get_python_code())
            conn.send(ujson.dumps(sumorobot.get_python_code()))
        elif b'get_blockly_code' in data:
            print(sumorobot.get_blockly_code())
            conn.send(ujson.dumps(sumorobot.get_blockly_code()))
        elif b'set_blockly_code' in data:
            data = ujson.loads(data)
            print(data)
            sumorobot.blockly_code = data['val']
        elif b'set_python_code' in data:
            data = ujson.loads(data)
            print(data)
            sumorobot.python_code = data['val']
            data['val'] = data['val'].replace(";;", "\n")
            #print("main.py code=", data['val'])
            sumorobot.compiled_python_code = compile(data['val'], "snippet", "exec")
        elif b'calibrate_line_value' in data:
            sumorobot.calibrate_line_value()
            #print('main.py: calibrate_line_value')
        elif b'set_line_threshold' in data:
            data = ujson.loads(data)
            sumorobot.set_line_threshold(int(data['val']))
            #print('main.py: set_line_threshold')
        elif b'Gone' in data:
            print("main.py: server said 410 Gone, attempting to reconnect...")
            #conn = uwebsockets.connect(url)
        else:
            print("main.py: unknown cmd=", data)

# Try to load the user code
try:
    with open("code.py", "r") as code:
        temp = code.read()
        sumorobot.python_code = temp
        sumorobot.compiled_python_code = compile(temp, "snippet", "exec")
except:
    print("main.py: error loading code.py file")

# Start the code processing thread
_thread.start_new_thread(step, ())

# Wait for WiFi to get connected
while not wlan.isconnected():
    sleep_ms(100)

# Connect to the websocket
uri = "ws://%s/p2p/sumo-%s/browser/" % (config['sumo_server'], config['sumo_id'])
conn = uwebsockets.connect(uri)

# Set X seconds timeout for socket reads
conn.settimeout(1)

# Stop bootup blinking
timer.deinit()

# WiFi is connected
sumorobot.is_wifi_connected = True
# Indicate that the WebSocket is connected
sumorobot.set_led(STATUS, True)

# Start the Websocket processing thread
_thread.start_new_thread(ws_handler, ())
