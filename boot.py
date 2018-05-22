import ujson
import network
from hal import *
from time import sleep

#print("Press Ctrl-C to stop boot script...")
sleep(0.2)

# open and parse the config file
config = None
with open("config.json", "r") as config_file:
    config = ujson.load(config_file)

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
            #print("connecting to: " + ssid)
            # start to connect to the pre-configured network
            wlan.connect(ssid, config["wifis"][ssid])
            break

# clean up
import gc
gc.collect()
