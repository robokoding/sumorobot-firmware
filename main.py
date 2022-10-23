import utime
import _thread
import ubluetooth
import micropython

from hal import *
# Loading libraries takes ca 400ms


# BLE events
_IRQ_CENTRAL_CONNECT = micropython.const(1)
_IRQ_CENTRAL_DISCONNECT = micropython.const(2)
_IRQ_GATTS_WRITE = micropython.const(3)

# SumoRobot functionality
sumorobot = Sumorobot()


def advertise_ble_name(name):
    payload = b'\x02\x01\x02' + bytes([len(name) + 1])
    payload += b'\x09' + name.encode()
    ble.gap_advertise(100, payload)


def update_battery_level(timer):
    if conn_handle is not None:
        battery_level = sumorobot.get_battery_level()
        ble.gatts_notify(conn_handle, battery, bytes([battery_level]))


def sensor_feedback_thread():
    while True:
        # Leave time to process other threads
        utime.sleep_ms(50)
        # Execute to see LED feedback for sensors
        sumorobot.update_sensor_feedback()


def code_process_thread():
    global prev_bat_level, python_code

    while True:
        # Leave time to process other threads
        utime.sleep_ms(50)

        # When no code to execute
        if python_code == b'':
            continue

        sumorobot.terminate = False

        # Try to execute the Python code
        try:
            exec(compile(python_code, "snippet", 'exec'))
        except Exception as error:
            print("main.py: the python code had errors:", error)
        finally:
            print("main.py: finized python code execution")
            # Erase the code
            python_code = b''
            # Stop the robot
            sumorobot.move(STOP)


# The BLE handler thread
def ble_handler(event, data):
    global conn_handle, python_code, temp_python_code

    if event is _IRQ_CENTRAL_CONNECT:
        conn_handle, _, _, = data
        # Turn ON the status LED
        sumorobot.set_led(STATUS, True)
        update_battery_level(None)
        advertise_ble_name(sumorobot.config['sumorobot_name'])
    elif event is _IRQ_CENTRAL_DISCONNECT:
        conn_handle = None
        # Turn OFF status LED
        sumorobot.set_led(STATUS, False)
        # Advertise with name
        advertise_ble_name(sumorobot.config['sumorobot_name'])
    elif event is _IRQ_GATTS_WRITE:
        # Read the command
        cmd = ble.gatts_read(rx)
        print(cmd)

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
            ble.gatts_notify(conn_handle, tx, sumorobot.get_sensor_scope())
        elif b'<config>' in cmd:
            ble.gatts_notify(conn_handle, tx, sumorobot.get_configuration_scope())
        elif b'<pwm>' in cmd:
            servo, speed = cmd[5:].decode().split(',')
            servo = LEFT if servo == 'LEFT' else RIGHT
            sumorobot.pwm[servo].duty(int(speed)) 
        elif b'<code>' in cmd:
            temp_python_code = b'\n'
        elif b'<code/>' in cmd:
            python_code = temp_python_code
            temp_python_code = b''
        elif temp_python_code != b'':
            temp_python_code += cmd
        else:
            temp_python_code = b''
            print("main.py: unknown cmd=", cmd)


conn_handle = None
temp_python_code = b''
python_code = b''

# When boot code exists
if sumorobot.config['boot_code'] in root_files:
    print("main.py: trying to load", sumorobot.config['boot_code'])
    # Try to load and compile the boot code
    try:
        with open(sumorobot.config['boot_code'], 'r') as file:
            boot_code = file.read()
            compile(boot_code, "snippet", 'exec')
            python_code = boot_code
    except Exception as error:
        print("main.py:", sumorobot.config['boot_code'], "compilation failed:", error)

# Start BLE
ble = ubluetooth.BLE()
ble.config(gap_name=sumorobot.config['sumorobot_name'])
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

# Start the threads
_thread.start_new_thread(code_process_thread, ())
_thread.start_new_thread(sensor_feedback_thread, ())

# Start BLE battery percentage update timer
battery_timer = machine.Timer(machine.Timer.PERIODIC)
battery_timer.init(period=3000, callback=update_battery_level)

# Clean up
import gc
gc.collect()
