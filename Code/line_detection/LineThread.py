import threading
import time

class LineThread(threading.Thread):
    def __init__(self, cam, detector, controller, roi1, roi2):
        threading.Thread.__init__(self)
        self.cam = cam
        self.detector = detector
        self.roi1 = roi1
        self.roi2 = roi2
        self.latestFrame = None
        self.running = True
        self.controller = controller

    def stop(self):
        self.running = False

    def run(self):
        self.controller.drive(50)
        while self.running:
            self.controller.drive(50)
            frame = self.cam.getFrame()
            frame = frame[self.roi1[0]:self.roi1[1], self.roi2[0]:self.roi2[1]]
            intersection, frame = self.detector.getIntersection(frame)
            self.latestFrame = frame
            if intersection is not None:
                if intersection[1] >= self.roi1[1]*0.6:
                    if self.cam.camPos == "left":
                        self.controller.steer(30, "right")
                        print("steering right")
                    elif self.cam.camPos == "right":
                        self.controller.steer(30, "left")
                        print("steering left")
                elif intersection[1] >= self.roi1[1]*0.7:
                    if self.cam.camPos == "left":
                        self.controller.steer(50, "right")
                        print("steering right")
                    elif self.cam.camPos == "right":
                        self.controller.steer(50, "left")
                        print("steering left")
            time.sleep(1/30)
        self.cam.release()