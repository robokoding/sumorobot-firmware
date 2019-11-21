def send():
    while True:
        try:
            ble.gatts_notify(conn_handle, tx, sumorobot.get_sensor_scope())
        except:
            print('main.py: tx error')
        sleep_ms(250)

# The code processing thread
def step():
    global python_code

    while True:
        # Execute to see LED feedback for sensors
        sumorobot.update_sensor_feedback()
        # Try to execute the Python code
        try:
            #if conn_handle != None:
                # Send sensor values
                #ble.gatts_notify(conn_handle, tx, sumorobot.get_sensor_scope())
            #sumorobot.python_code = compile(python_code, "snippet", "exec")
            exec(python_code)
        except:
            print("main.py: the code sent had errors")
        finally:
            if python_code != b'':
                # Erase the code
                python_code = b''
        # Leave time to process other code
        sleep_ms(50)

# The BLE data processing thread
def ble_data_handler(event, data):
    global conn_handle, python_code, temp_python_code

    # 1: Connection event
    if event == 1:
        conn_handle, _, _, = data
        # Turn ON the status LED
        sumorobot.set_led(STATUS, True)
    # 2: Disconnection event
    elif event == 2:
        conn_handle = None
        # Turn OFF status LED
        sumorobot.set_led(STATUS, False)
        # Advertise with name
        ble_name = bytes(sumorobot.config['sumorobot_name'], 'ascii')
        ble_name = bytearray((len(ble_name) + 1, 0x09)) + ble_name
        ble.gap_advertise(100, bytearray('\x02\x01\x02') + ble_name)
    # 4: Data event
    elif event == 4:
        # Read the data
        cmd = ble.gatts_read(rx)

        if b';;' in cmd:
            if temp_python_code != b'':
                temp_python_code += cmd
                python_code = temp_python_code.replace(b';;', b'')
                temp_python_code = b''
                print(python_code)
            else:
                temp_python_code = cmd
        elif temp_python_code != b'':
            temp_python_code += cmd
        elif b'forward' in cmd:
            sumorobot.move(FORWARD)
        elif b'backward' in cmd:
            sumorobot.move(BACKWARD)
        elif b'right' in cmd:
            sumorobot.move(RIGHT)
        elif b'left' in cmd:
            sumorobot.move(LEFT)
        elif b'stop' in cmd:
            python_code = b''
            sumorobot.move(STOP)
        elif b'sensors' in cmd:
            pass
        else:
            print('main.py: unknown cmd=', cmd)

# When user code (code.py) exists
if 'code.py' in os.listdir():
    print('main.py: trying to load code.py')
    # Try to load the user code
    try:
        with open("code.py", "r") as code:
            python_code = compile(code.read(), "snippet", "exec")
    except:
        print("main.py: code.py execution failed")

conn_handle = None
temp_python_code = b''
python_code = b''

# Configuration BLE
ble = bluetooth.BLE()
ble.active(True)

# BLE data handling        
ble.irq(ble_data_handler)

# BLE GATT Server
UART_UUID = bluetooth.UUID('6E400001-B5A3-F393-E0A9-E50E24DCCA9E')
UART_TX = (bluetooth.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E'), bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,)
UART_RX = (bluetooth.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E'), bluetooth.FLAG_WRITE,)
UART_SERVICE = (UART_UUID, (UART_TX, UART_RX,),)
SERVICES = (UART_SERVICE,)
((tx, rx,),) = ble.gatts_register_services(SERVICES)

# Advertise with name
ble_name = bytes(sumorobot.config["sumorobot_name"], 'ascii')
ble_name = bytearray((len(ble_name) + 1, 0x09)) + ble_name
ble.gap_advertise(100, bytearray('\x02\x01\x02') + ble_name)

# Start the code processing thread
_thread.start_new_thread(step, ())

# Start the sensor data sending thread
_thread.start_new_thread(send, ())