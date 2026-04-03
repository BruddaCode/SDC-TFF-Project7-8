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
        self.steerRoi = (roi1[1]*0.3, roi1[1]*0.8)

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
                if self.steerRoi[0] <= intersection[1] <= self.steerRoi[1]:
                    percentage = 100 * ((intersection[1] - self.steerRoi[0]) / (self.steerRoi[1] - self.steerRoi[0]))
                    if self.cam.camPos == "left":
                        self.controller.steer(percentage, "right")
                        print("steering right")
                    elif self.cam.camPos == "right":
                        self.controller.steer(percentage, "left")
                        print("steering left")
                elif intersection[1] > self.steerRoi[1]:
                    if self.cam.camPos == "left":
                        self.controller.steer(100, "right")
                        print("steering right")
                    elif self.cam.camPos == "right":
                        self.controller.steer(100, "left")
                        print("steering left")
            time.sleep(1/30)
        self.cam.release()