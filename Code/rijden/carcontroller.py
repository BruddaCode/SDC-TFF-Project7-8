from rijden.steer import steer_message
from rijden.motor import forward_message
from rijden.brake import set_brake_force_message
import can
import struct

"""
This module handles the control of the car(kart) by sending messages to the bus.

main.py will use this to control the car's movement, steering, and braking.

"""
class CarController:
    def __init__(self):
        self.bus = can.Bus(interface='socketcan', channel='can0', bitrate=500000)

    def drive(self, speed: int):
        if not (0 <= speed <= 100):
            raise ValueError("Speed must be between 0 and 100")
        
        message = can.Message(
            arbitration_id=0x330,
            data=[speed, 0, 1, 0, 0, 0, 0, 0],
            is_extended_id=False
        )
        self.bus.send(message)

    def steer(self, angle: int, direction: str):
        if not (0 <= angle <= 100):
            raise ValueError("Angle must be between 0 and 100")
        
        if direction == "left":
            angleBytes = struct.pack('<f', angle/100*(-1.25))
        if direction == "right":
            angleBytes = struct.pack('<f', angle/100*1.25)

        message = can.Message(
            arbitration_id=0x220,
            data=[*angleBytes, 0, 0, 0, 0],
            is_extended_id=False
        )
        self.bus.send(message)

    def brake(self, force: int = 100):
        if not (0 <= force <= 100):
            raise ValueError("Force must be between 0 and 100")
        
        message = can.Message(
            arbitration_id=0x110,
            data=[force, 0, 0, 0, 0, 0, 0, 0],
            is_extended_id=False
        )
        self.bus.send(message)

    def stop(self):
        self.drive(0)
        self.brake()