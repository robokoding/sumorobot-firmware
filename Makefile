#!/bin/bash

SERIAL_PORT=/dev/ttyUSB0

ifeq (,$(wildcard $(SERIAL_PORT)))
    SERIAL_PORT=/dev/tty.usbserial-1410
endif

ifeq (,$(wildcard $(SERIAL_PORT)))
    SERIAL_PORT=/dev/tty.usbserial-1420
endif

ifeq (,$(wildcard $(SERIAL_PORT)))
    SERIAL_PORT=/dev/tty.SLAB_USBtoUART
endif

all: flash delay config update reset

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

flash:
	esptool.py -p $(SERIAL_PORT) -b 460800 erase_flash
	esptool.py -p $(SERIAL_PORT) -b 460800 write_flash --flash_mode dio 0x1000 esp32*.bin

serial:
	picocom --baud 115200 $(SERIAL_PORT)
