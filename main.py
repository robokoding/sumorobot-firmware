import _thread
import ubinascii
import uwebsockets

# to remember WiFi disconnects
has_wifi_connection = False
# WebSocket connection
conn = None
# blockly highlihgt WebSocket connection
conn_highlight = None
# extract a unique name for the robot from the device MAC address
name = "sumo-%s" % ubinascii.hexlify(wlan.config("mac")[-3:]).decode("ascii")

# remote server
url = "ws://iot.koodur.com:80/p2p/" + name + "/browser/"
url_highlight = "ws://iot.koodur.com:80/p2p/" + name + "-highlight/browser/"

# local server
#url = "ws://10.42.0.1:80/p2p/" + name + "/browser/"
#url_highlight = "ws://10.42.0.1:80/p2p/" + name + "-highlight/browser/"

# code to execute
ast = ""
# scope, info to be sent to the client
scope = dict()
# SumoRobot object
sumorobot = None

def step():
    global scope

    while True:
        # execute to see LED feedback for sensors
        sumorobot.is_opponent()
        sumorobot.is_line(LEFT)
        sumorobot.is_line(RIGHT)
        # update scope
        scope = dict(
            line_left = sumorobot.get_line(LEFT),
            line_right = sumorobot.get_line(RIGHT),
            opponent = sumorobot.get_opponent_distance(),
            battery_voltage = sumorobot.get_battery_voltage(),
        )
        # execute code
        exec(ast)
        # when robot was stopped
        if sumorobot.terminate:
            # disable forceful termination of delays in code
            sumorobot.terminate = False
            # stop the robot
            sumorobot.move(STOP)
        # leave time to process WebSocket commands
        sleep_ms(50)

def ws_handler():
    global ast
    global conn
    global has_wifi_connection

    while True:
        # when WiFi is connected
        if wlan.isconnected():
            # when WiFi has just been reconnected
            if not has_wifi_connection:
                conn = uwebsockets.connect(url)
                sumorobot.set_led(STATUS, True)
                has_wifi_connection = True
        else: # when WiFi is not connected
            # when WiFi has just been disconnected
            if has_wifi_connection:
                sumorobot.set_led(STATUS, False)
                has_wifi_connection = False
            # continue to wait for a WiFi connection
            continue

        try:
            fin, opcode, data = conn.read_frame()
        except: # urror
            # socket timeout, no data received
            print("socket timeout")
            # continue to read again from socket
            continue

        if data == b"forward":
            #print("Going forward")
            ast = ""
            sumorobot.move(FORWARD)
        elif data == b"backward":
            #print("Going backward")
            ast = ""
            sumorobot.move(BACKWARD)
        elif data == b"right":
            #print("Going right")
            ast = ""
            sumorobot.move(RIGHT)
        elif data == b"left":
            #print("Going left")
            ast = ""
            sumorobot.move(LEFT)
        elif data == b"kick":
            conn.send(repr(scope))
        elif data == b"ping":
            conn.send(repr(scope))
        elif data.startswith("start:"):
            #print("Got code:", data[6:])
            ast = compile(data[6:], "snippet", "exec")
        elif data == b"stop":
            ast = ""
            sumorobot.move(STOP)
            # for terminating delays in code
            sumorobot.terminate = True
            #print("Got stop")
        elif data == b"calibrate_line":
            sumorobot.calibrate_line()
            #print("Got calibrate")
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

# set X seconds timeout for socket reads
conn.settimeout(1)

# send a ping to the robot
print("Sending ping")
conn.send("{'ping': true}")
conn.send("{'ip': '" + wlan.ifconfig()[0] + "'}")

# connect to the blockly highlight websocket
conn_highlight = uwebsockets.connect(url_highlight)

# initialize SumoRobot object
sumorobot = Sumorobot(conn_highlight.send)

# indicate that the WebSocket is connected
sumorobot.set_led(STATUS, True)

print("Starting WebSocket and code loop")
# start the code processing thread
_thread.start_new_thread(step, ())
# start the Websocket processing thread
_thread.start_new_thread(ws_handler, ())
