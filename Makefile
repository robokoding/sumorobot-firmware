all:
	ampy -p /dev/tty.SLAB_USBtoUART put hal.py
	ampy -p /dev/tty.SLAB_USBtoUART put main.py
	ampy -p /dev/tty.SLAB_USBtoUART put boot.py
	ampy -p /dev/tty.SLAB_USBtoUART put wifis.json
	ampy -p /dev/tty.SLAB_USBtoUART put uwebsockets.py

update:
	ampy -p /dev/tty.SLAB_USBtoUART put hal.py
        ampy -p /dev/tty.SLAB_USBtoUART put main.py
        ampy -p /dev/tty.SLAB_USBtoUART put boot.py

wifis:
	ampy -p /dev/tty.SLAB_USBtoUART put wifis.json

flash:
	esptool.py -p /dev/tty.SLAB_USBtoUART -b 460800 erase_flash
	esptool.py -p /dev/tty.SLAB_USBtoUART -b 460800 write_flash --flash_mode dio 0x1000 esp32-*.bin
