#!/bin/bash

# When this baud does not work, try 115200
FLASH_BAUD := 230400

# Image to flash
FLASH_IMAGE := sumofirmware.bin

# Try to automatically find the serialport
SERIAL_PORT := $(shell find /dev -iname "tty*usb*")

all: erase flash delay config update reset

delay:
	sleep 3

reset:
	esptool.py -p $(SERIAL_PORT) --after hard_reset read_mac

update:
	ampy -d 0.5 -p $(SERIAL_PORT) put hal.py
	ampy -d 0.5 -p $(SERIAL_PORT) put main.py
	ampy -d 0.5 -p $(SERIAL_PORT) put boot.py

config:
	ampy -d 0.5 -p $(SERIAL_PORT) put config.json

erase:
	esptool.py -p $(SERIAL_PORT) -b $(FLASH_BAUD) erase_flash

image:
	esptool.py -p $(SERIAL_PORT) -b $(FLASH_BAUD) read_flash 0x1000 0x3FF000 sumofirmware.bin

flash:
	esptool.py -p $(SERIAL_PORT) -b $(FLASH_BAUD) write_flash --flash_mode dio 0x1000 $(FLASH_IMAGE)

serial:
	picocom --baud 115200 -q $(SERIAL_PORT)

