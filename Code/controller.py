from evdev import InputDevice, list_devices

controller = None

for path in list_devices():
	dev = InputDevice(path)
	print(f"Checking device: {dev.name}")
	if "Xbox" in dev.name or "Controller" in dev.name:
		print(f"Found controller: {dev.path}")
		break
	
print("No controller found.")