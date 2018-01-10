# Just in case prevent boot loops
from hal import *
from time import sleep
import socket, re, os, uwebsockets, network, binascii, ujson

print("Press Ctrl-C to stop boot script...")
sleep(0.2)

# read WiFi config
wifis = ujson.loads(open("wifis.json", "r").read())
#print(wifis)

# Connect to WiFi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if not wlan.isconnected():
    networks = wlan.scan()
    for network in networks:
        ssid = network[0].decode("utf-8")
        if ssid in wifis.keys():
            print("connecting to: " + ssid)
            wlan.connect(ssid, wifis[ssid])
            break

#print('network config:', wlan.ifconfig())
#sleep(1)

# Clean up
import gc
gc.collect()
