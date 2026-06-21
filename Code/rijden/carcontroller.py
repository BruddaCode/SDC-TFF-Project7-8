import struct
import can


class CarController:
    def __init__(self):
        #? this initializes the CAN bus interface and sets up the periodic messages for driving, steering and braking.
        #? the bitrate and messagespeed is a set value that doesnt need to be changed, as this would make the car not respond to the commands anymore.
        self.bus = can.Bus(interface='socketcan', channel='can0', bitrate=500000)
        self.canMessageSpeed = 0.04
        self.started = False
        
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

    #? this function drives the car at a given speed, which is a value between 0 and 255, where 0 is stopped and 255 is full speed
    #? maybe for convenience, the speed could be a percentage of the maximum speed, but this is not implemented yet
    def drive(self, speed: int):
        if not (0 <= speed <= 255):
            raise ValueError("Speed must be between 0 and 255")
        
        self.drivemsg.data = [speed, 0, 1, 0, 0, 0, 0, 0]
        self.drivetask.modify_data(self.drivemsg)

    #? this function steers the car at a given angle, which is a value between -100 and 100, where -100 is full left and 100 is full right (which in this case is percentage based)
    #? the angle is converted to a value between -1.25 and 1.25, which is the range of the steering angle in radians
    def steer(self, angle: int):
        if not (-100 <= angle <= 100):
            raise ValueError("Angle must be between -100 and 100")
        
        angle = round((angle/100*1.25), 2)
        self.steermsg.data = list(bytearray(struct.pack('f', angle))) + [0, 0, 195, 0]
        self.steertask.modify_data(self.steermsg)

    #? this function applies the brakes to the car at a given force, which is a value between 0 and 100, where 0 is no brake and 100 is full brake
    def brake(self, force: int = 100):
        if not (0 <= force <= 100):
            raise ValueError("Force must be between 0 and 100")
        
        self.brakemsg.data = [force, 0, 0, 0, 0, 0, 0, 0]
        self.braketask.modify_data(self.brakemsg)

    #? this function stops the car by setting the speed to 0 and applying the brakes at full force
    def stop(self):
        self.drive(0)
        self.brake()

    #? this function turns off the CAN bus interface, which is useful for shutting down the car safely
    def turnOffBus(self):
        self.bus.shutdown()