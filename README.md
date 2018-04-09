# sumorobot-firmware
[![Donate using Liberapay](https://liberapay.com/assets/widgets/donate.svg)](https://liberapay.com/robokoding/donate)  
The software that is running on the SumoRobots

# Instructions
* Change the SERIAL_PORT in the Makefile
* Add your WiFi networks to the config.json file
* Install [Python](https://www.python.org/downloads/)
* Install [esptool](https://github.com/espressif/esptool) (to communicate with the ESP32 board)
* Install [ampy](https://github.com/adafruit/ampy) (for uploading files)
* Download [the MicroPython binary](http://micropython.org/download#esp32) to this directory
* Upload the MicroPython binary and the SumoRobot firmware to your ESP32 (open a terminal and type: make all)

# Credits
* [K-SPACE MTÜ](https://k-space.ee/)
