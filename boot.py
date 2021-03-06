import os
import utime
import machine


# Give time to cancel this boot script
print("Press Ctrl-C to stop new boot script...")
utime.sleep_ms(1000)

root_files = os.listdir()
update_files = ['boot.py.new', 'main.py.new', 'hal.py.new']
files_to_update = []

# Check for FW updates and verify new FW files
for file in update_files:
    if file in root_files:
        print("boot.py: starting to update:", file)
        # Try to load the user code
        try:
            with open(file, 'r') as code:
                compile(code.read(), "snippet", 'exec')
            files_to_update.append(file)
        except Exception as error:
            print("boot.py:", file, "compilation failed:", error)
            files_to_update.clear()
            break

# If valid updates replace with new FW
for file in files_to_update:
    os.rename(file, file.replace('.new', ''))

# If updates, reboot to load new FW
if len(files_to_update) != 0:
    machine.reset()
