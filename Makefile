SERIAL_PORT=/dev/tty.SLAB_USBtoUART
#SERIAL_PORT=/dev/tty.wchusbserial1410
#SERIAL_PORT=/dev/ttyUSB0

all: flash delay libs config update reset

delay:
	sleep 3

reset:
	esptool.py -p $(SERIAL_PORT) --after hard_reset read_mac

libs:
	ampy -d 0.5 -p $(SERIAL_PORT) put uwebsockets.py

update:
	ampy -d 0.5 -p $(SERIAL_PORT) put hal.py
	ampy -d 0.5 -p $(SERIAL_PORT) put main.py
	ampy -d 0.5 -p $(SERIAL_PORT) put boot.py

config:
	ampy -d 0.5 -p $(SERIAL_PORT) put config.json

flash:
	esptool.py -p $(SERIAL_PORT) -b 460800 erase_flash
	esptool.py -p $(SERIAL_PORT) -b 460800 write_flash --flash_mode dio 0x1000 esp32-*.bin
