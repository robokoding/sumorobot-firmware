import ujson
import network
from hal import *
from utime import sleep_ms
from machine import Timer, Pin

print("Press Ctrl-C to stop boot script...")
sleep_ms(200)

# Open and parse the config file
with open("config.json", "r") as config_file:
    config = ujson.load(config_file)

# Initialize the SumoRobot object
sumorobot = Sumorobot(config)

# Indiacte booting with blinking status LED
timer = Timer(0)
sumorobot.toggle_led()
timer.init(period=2000, mode=Timer.PERIODIC, callback=sumorobot.toggle_led)

# Connect to WiFi
wlan = network.WLAN(network.STA_IF)
# Activate the WiFi interface
wlan.active(True)
# If not already connected
if not wlan.isconnected():
    # Scan for WiFi networks
    networks = wlan.scan()
    # Go trough all scanned WiFi networks
    for network in networks:
        # Extract the networks SSID
        ssid = network[0].decode("utf-8")
        # Check if the SSID is in the config file
        if ssid in config["wifis"].keys():
            # Start to connect to the pre-configured network
            wlan.connect(ssid, config["wifis"][ssid])
            break

# Clean up
import gc
gc.collect()
