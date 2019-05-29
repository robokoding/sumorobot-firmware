# The code processing thread
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

# The WebSocket processing thread
def ws_handler():
    global conn, watchdog_counter

    while True:
        # When WiFi has just been reconnected
        if wlan.isconnected() and not sumorobot.is_wifi_connected:
            print("main.py reconnected to Wi-Fi")
            # Stop blinking status LED
            timer.deinit()
            # Turn status LED to steady ON
            sumorobot.set_led(STATUS, True)
            sumorobot.is_wifi_connected = True
        # When WiFi has just been disconnected
        elif not wlan.isconnected() and sumorobot.is_wifi_connected:
            print("main.py lost Wi-Fi, reconnecting to Wi-Fi")
            # Reinitiate the Wi-Fi connection
            wlan.connect(ssid, config["wifis"][ssid])
            # Turn OFF status LED
            sumorobot.set_led(STATUS, False)
            sumorobot.is_wifi_connected = False
            # Start bliking status LED
            timer.init(period=2000, mode=Timer.PERIODIC, callback=sumorobot.toggle_led)
        elif not wlan.isconnected():
            # Continue to wait for a WiFi connection
            continue

        data = None
        try: # Try to read from the WebSocket
            data = conn.recv()
        except: # Socket timeout, no data received
            # Increment watchdog counter
            watchdog_counter += 1
            # When Wi-Fi is connected and X-th exception happened
            # Try reconnecting to the WebSocket server
            if wlan.isconnected() and watchdog_counter == 3:
                print("main.py WebSocket timeout, reconnecting")
                conn = uwebsockets.connect(uri)
                watchdog_counter = 0
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
        elif b'get_threshold_scope' in data:
            conn.send(ujson.dumps(sumorobot.get_threshold_scope()))
        elif b'get_sensor_scope' in data:
            conn.send(ujson.dumps(sumorobot.get_sensor_scope()))
        elif b'get_python_code' in data:
            #print("main.py sending python code=", sumorobot.get_python_code())
            conn.send(ujson.dumps(sumorobot.get_python_code()))
        elif b'get_blockly_code' in data:
            #print("main.py sending blockly code=", sumorobot.get_blockly_code())
            conn.send(ujson.dumps(sumorobot.get_blockly_code()))
        elif b'get_firmware_version' in data:
            #print("main.py get_firmware_version")
            conn.send(ujson.dumps(sumorobot.get_firmware_version()))
        elif b'toggle_sensor_feedback' in data:
            data = ujson.loads(data)
            sumorobot.sensor_feedback = not sumorobot.sensor_feedback
        elif b'set_blockly_code' in data:
            data = ujson.loads(data)
            #print("main.py Blockly code=", data['val'])
            sumorobot.blockly_code = data['val']
        elif b'set_python_code' in data:
            data = ujson.loads(data)
            sumorobot.python_code = data['val']
            data['val'] = data['val'].replace(";;", "\n")
            #print("main.py python code=", data['val'])
            sumorobot.compiled_python_code = compile(data['val'], "snippet", "exec")
        elif b'calibrate_line_value' in data:
            sumorobot.calibrate_line_value()
            #print("main.py: calibrate_line_value")
        elif b'set_line_threshold' in data:
            data = ujson.loads(data)
            sumorobot.set_line_threshold(int(data['val']))
            #print("main.py: set_line_threshold")
        elif b'set_ultrasonic_threshold' in data:
            data = ujson.loads(data)
            sumorobot.set_ultrasonic_threshold(int(data['val']))
            #print("main.py: set_ultrasonic_threshold")
        elif b'Gone' in data:
            print("main.py: server said 410 Gone, attempting to reconnect...")
            #conn = uwebsockets.connect(url)
        else:
            print("main.py: unknown cmd=", data)

# When user code (copy.py) exists
if 'code.py' in os.listdir():
    print("main.py: loading user code")
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

# Wifi watchdog counter
watchdog_counter = 0
# Wait for WiFi to get connected
while not wlan.isconnected():
    sleep_ms(100)
    watchdog_counter += 1
    # When Wi-Fi didn't connect in X seconds
    if watchdog_counter == 30:
        print("main.py reconnecting to Wi-Fi")
        # Reinitiate the Wi-Fi connection
        wlan.connect(ssid, config["wifis"][ssid])

# Restart watchdog counter
watchdog_counter = 0

# Connect to the websocket
uri = "ws://%s/p2p/sumo-%s/browser/" % (config['sumo_server'], config['sumo_id'])
conn = uwebsockets.connect(uri)

# Stop bootup blinking
timer.deinit()

# WiFi is connected
sumorobot.is_wifi_connected = True
# Indicate that the WebSocket is connected
sumorobot.set_led(STATUS, True)

# Start the Websocket processing thread
_thread.start_new_thread(ws_handler, ())
