from hal import *
from time import sleep
import socket, re, os, uwebsockets, network, binascii, ujson

print("Press Ctrl-C to stop boot script...")
sleep(0.2)

# read the config file
config = ujson.loads(open("config.json", "r").read())
print(config)

# connect to WiFi
wlan = network.WLAN(network.STA_IF)
# activate the WiFi interface
wlan.active(True)
# if not already connected
if not wlan.isconnected():
    # scan for WiFi networks
    networks = wlan.scan()
    # go trough all scanned WiFi networks
    for network in networks:
        # extract the networks SSID
        ssid = network[0].decode("utf-8")
        # check if the SSID is in the config file
        if ssid in config["wifis"].keys():
            print("connecting to: " + ssid)
            # start to connect to the pre-configured network
            wlan.connect(ssid, wifis[ssid])
            break

# Clean up
import gc
gc.collect()
