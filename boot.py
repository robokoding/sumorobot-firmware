# Import functions from time library
from utime import ticks_us, sleep_us, sleep_ms

# Give time to cancel boot script
print("Press Ctrl-C to stop boot script...")
sleep_ms(200)

# Import libraries
import os
import ujson
import _thread
import bluetooth
from hal import *
# Loading libraries takes ca 400ms

# Open and parse the config file
with open("config.json", "r") as config_file:
    config = ujson.load(config_file)

# Initialize the SumoRobot object
s = sumorobot = Sumorobot(config)

# Clean up
import gc
gc.collect()
