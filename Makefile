#!/bin/bash

#SERIAL_PORT=/dev/ttyUSB0
SERIAL_PORT=/dev/tty.usbserial-1410
#SERIAL_PORT=/dev/tty.SLAB_USBtoUART
#SERIAL_PORT=/dev/tty.wchusbserial1410

all: flash

flash:
	esptool.py -p $(SERIAL_PORT) -b 460800 erase_flash
	esptool.py -p $(SERIAL_PORT) -b 460800 write_flash --flash_mode dio 0x1000 esp32-*.bin
