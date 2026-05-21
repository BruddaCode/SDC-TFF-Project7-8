import struct
import can

"""
This module handles the control of the car(kart) by sending messages to the bus.

main.py will use this to control the car's movement, steering, and braking.

"""
class CarController:
    def __init__(self):
        self.bus = can.Bus(interface='socketcan', channel='can0', bitrate=500000)
        self.canMessageSpeed = 0.04
        
        self.brakemsg = can.Message(
            arbitration_id=0x110,
            data=[0, 0, 0, 0, 0, 0, 0, 0],
            is_extended_id=False
        )
        self.braketask = self.bus.send_periodic(self.brakemsg,self.canMessageSpeed)
        
        self.steermsg = can.Message(
            arbitration_id=0x220,
            data=[0, 0, 0, 0, 0, 0, 195, 0],
            is_extended_id=False
        )
        self.steertask = self.bus.send_periodic(self.steermsg,self.canMessageSpeed)

        self.drivemsg = can.Message(
            arbitration_id=0x330,
            data=[0, 0, 1, 0, 0, 0, 0, 0],
            is_extended_id=False
        )
        self.drivetask = self.bus.send_periodic(self.drivemsg,self.canMessageSpeed)

    def drive(self, speed: int):
        if not (0 <= speed <= 255):
            raise ValueError("Speed must be between 0 and 255")
        
        if speed >=1:
            self.brake(0)
        
        message = can.Message(
            arbitration_id=0x330,
            data=[speed, 0, 1, 0, 0, 0, 0, 0],
            is_extended_id=False
        )
        self.bus.send_periodic(message,self.canMessageSpeed)

    def steer(self, angle: int,):
        if not (-100 <= angle <= 100):
            raise ValueError("Angle must be between -100 and 100")
        angle = angle/100*1.25
        print(angle)
        angleBytes = list(bytearray(struct.pack('f', angle)))
        self.steermsg.data[0:4] = angleBytes
        self.steertask.modify_data(self.steermsg)

    def brake(self, force: int = 100):
        if not (0 <= force <= 100):
            raise ValueError("Force must be between 0 and 100")
        
        if force >=1:
            self.drive(0)
        
        message = can.Message(
            arbitration_id=0x110,
            data=[force, 0, 0, 0, 0, 0, 0, 0],
            is_extended_id=False
        )
        self.bus.send_periodic(message,self.canMessageSpeed)

    def stop(self):
        self.drive(0)
        self.brake()

    def turnOffBus(self):
        self.bus.shutdown()