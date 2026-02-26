import sys
import numpy as np
from rplidar import RPLidar


PORT_NAME = '/dev/ttyUSB0'
BAUDRATE = 256000
TIMEOUT = 1


def run():
    '''Main function'''
    lidar = RPLidar(port=PORT_NAME, baudrate=BAUDRATE, timeout=TIMEOUT)
    data = []
    for scan in lidar.iter_scans():
        detected_front = False
        detected_left = False
        detected_right = False
        
        for _, angle, distance in scan:
            # Front: angle <= 195° or >= 165°
            if 165 < angle < 195:
                if distance < 500:
                    detected_front = True
            # Front-left: 15° < angle < 90°
            elif 15 < angle < 90:
                if distance < 500:
                    detected_left = True
            # Front-right: 270° < angle < 345°
            elif 270 < angle < 345:
                if distance < 500:
                    detected_right = True
        data.append((detected_front, detected_left, detected_right))
        print(scan)

run()