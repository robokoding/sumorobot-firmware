# Import functions from time library
from utime import ticks_us, sleep_us, sleep_ms

# Give time to cancel boot script
print("Press Ctrl-C to stop boot script...")
sleep_ms(200)

# Import libraries
import os
import ujson
import network
import _thread
import uwebsockets
from machine import Timer, reset
from hal import *
# Loading libraries takes ca 400ms

# Open and parse the config file
with open("config.json", "r") as config_file:
    config = ujson.load(config_file)

# Initialize the SumoRobot object
sumorobot = Sumorobot(config)

# Indiacte booting with blinking status LED
timer = Timer(0)
timer.init(period=2000, mode=Timer.PERIODIC, callback=sumorobot.toggle_led)

# Connected Wi-Fi SSID
ssid = None

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
        temp_ssid = network[0].decode("utf-8")
        # Check if the SSID is in the config file
        if temp_ssid in config["wifis"].keys():
            ssid = temp_ssid
            # Start to connect to the pre-configured network
            wlan.connect(ssid, config["wifis"][ssid])
            break

# Clean up
import gc
gc.collect()
