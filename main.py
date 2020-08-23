import ujson
import struct
import _thread
import ubluetooth
from machine import Timer
from micropython import const

from hal import *
# Loading libraries takes ca 400ms

# BLE events
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_READ_REQUEST = const(4)

# Open and parse the config file
with open('config.json', 'r') as config_file:
    config = ujson.load(config_file)

# Initialize the SumoRobot object
sumorobot = Sumorobot(config)

# Advertise BLE name (SumoRobot name)
def advertise_ble_name(name):
    ble_name = bytes(name, 'ascii')
    ble_name = bytearray((len(ble_name) + 1, 0x09)) + ble_name
    ble.gap_advertise(100, bytearray('\x02\x01\x02') + ble_name)

def update_battery_level(timer):
    if conn_handle is not None:
        battery_level = sumorobot.get_battery_level()
        ble.gatts_notify(conn_handle, battery, bytes([battery_level]))

# The code processing thread
def process():
    global prev_bat_level, python_code

    while True:
        # Leave time to process other code
        sleep_ms(50)
        # Execute to see LED feedback for sensors
        sumorobot.update_sensor_feedback()

        # When no code to execute
        if python_code == b'':
            continue

        # Try to execute the Python code
        try:
            python_code = compile(python_code, "snippet", 'exec')
            exec(python_code)
        except:
            print("main.py: the code sent had errors")
        finally:
            print("main.py: finized execution")
            # Erase the code
            python_code = b''
            # Stop the robot
            sumorobot.move(STOP)
            # Cancel code termination
            sumorobot.terminate = False

# The BLE handler thread
def ble_handler(event, data):
    global conn_handle, python_code, temp_python_code

    if event is _IRQ_CENTRAL_CONNECT:
        conn_handle, _, _, = data
        # Turn ON the status LED
        sumorobot.set_led(STATUS, True)
        update_battery_level(None)
    elif event is _IRQ_CENTRAL_DISCONNECT:
        conn_handle = None
        # Turn OFF status LED
        sumorobot.set_led(STATUS, False)
        # Advertise with name
        advertise_ble_name(sumorobot.config['sumorobot_name'])
    elif event is _IRQ_GATTS_READ_REQUEST:
        # Read the command
        cmd = ble.gatts_read(rx)

        if b'<stop>' in cmd:
            python_code = b''
            sumorobot.move(STOP)
            sumorobot.terminate = True
        elif b'<forward>' in cmd:
            python_code = b''
            sumorobot.move(FORWARD)
        elif b'<backward>' in cmd:
            python_code = b''
            sumorobot.move(BACKWARD)
        elif b'<left>' in cmd:
            python_code = b''
            sumorobot.move(LEFT)
        elif b'<right>' in cmd:
            python_code = b''
            sumorobot.move(RIGHT)
        elif b'<sensors>' in cmd:
            print(sumorobot.get_sensor_scope())
            ble.gatts_notify(conn_handle, tx, sumorobot.get_sensor_scope())
        elif b'<code>' in cmd:
            temp_python_code = b'\n'
        elif b'<code/>' in cmd:
            python_code = temp_python_code
            temp_python_code = b''
        elif temp_python_code != b'':
            temp_python_code += cmd
        else:
            temp_python_code = b''
            print("main.py: unknown cmd=" + cmd)

conn_handle = None
temp_python_code = b''
python_code = b''

# When user code (code.py) exists
if 'code.py' in root_files:
    print("main.py: trying to load code.py")
    # Try to load the user code
    try:
        with open('code.py', 'r') as code:
            python_code = compile(code.read(), "snippet", 'exec')
    except:
        print("main.py: code.py compilation failed")

# Start BLE
ble = ubluetooth.BLE()
ble.active(True)

# Register the BLE hander
ble.irq(ble_handler)

# BLE info serivce
INFO_SERVICE_UUID = ubluetooth.UUID(0x180a)
MODEL_CHARACTERISTIC = (ubluetooth.UUID(0x2a24), ubluetooth.FLAG_READ,)
FIRMWARE_CHARACTERISTIC = (ubluetooth.UUID(0x2a26), ubluetooth.FLAG_READ,)
MANUFACTURER_CHARACTERISTIC = (ubluetooth.UUID(0x2a29), ubluetooth.FLAG_READ,)
INFO_SERVICE = (INFO_SERVICE_UUID, (MODEL_CHARACTERISTIC, FIRMWARE_CHARACTERISTIC, MANUFACTURER_CHARACTERISTIC,),)

# BLE battery service
BATTERY_SERVICE_UUID = ubluetooth.UUID(0x180f)
BATTERY_CHARACTERISTIC = (ubluetooth.UUID(0x2a19), ubluetooth.FLAG_READ | ubluetooth.FLAG_NOTIFY,)
BATTERY_SERVICE = (BATTERY_SERVICE_UUID, (BATTERY_CHARACTERISTIC,),)

# BLE UART service
UART_SERVICE_UUID = ubluetooth.UUID('6E400001-B5A3-F393-E0A9-E50E24DCCA9E')
RX_CHARACTERISTIC = (ubluetooth.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E'), ubluetooth.FLAG_WRITE,)
TX_CHARACTERISTIC = (ubluetooth.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E'), ubluetooth.FLAG_READ | ubluetooth.FLAG_NOTIFY,)
UART_SERVICE = (UART_SERVICE_UUID, (TX_CHARACTERISTIC, RX_CHARACTERISTIC,),)

# Register BLE services
SERVICES = (INFO_SERVICE, BATTERY_SERVICE, UART_SERVICE,)
((model, firmware, manufacturer,), (battery,), (tx, rx,),) = ble.gatts_register_services(SERVICES)

# Set BLE info service values
ble.gatts_write(model, "SumoRobot")
ble.gatts_write(manufacturer, "RoboKoding LTD")
ble.gatts_write(firmware, sumorobot.config['firmware_version'])

# Start BLE advertising with name
advertise_ble_name(sumorobot.config['sumorobot_name'])

# Start the code processing thread
_thread.start_new_thread(process, ())

# Start BLE battery percentage update timer
battery_timer = Timer(Timer.PERIODIC)
battery_timer.init(period=3000, callback=update_battery_level)

# Clean up
import gc
gc.collect()
