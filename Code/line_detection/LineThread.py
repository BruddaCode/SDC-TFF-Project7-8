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
        steerflag1 = False
        steerflag2 = False
        self.controller.drive(255)
        while self.running:
            ret, frame = self.cam.getFrame()
            if not ret:
                break
            frame = frame[self.roi1[0]:self.roi1[1], self.roi2[0]:self.roi2[1]]
            intersection, frame = self.detector.getIntersection(frame)
            self.latestFrame = frame
            if intersection >= self.roi1[1]*0.6 and not steerflag1:
                steerflag1 = True
                steerflag2 = False
                if self.cam.camPos == "left":
                    self.controller.steer(50, "right")
                elif self.cam.camPos == "right":
                    self.controller.steer(50, "left")
            elif not steerflag2:
                steerflag1 = False
                steerflag2 = True
                self.controller.steer(0, "left")
            time.sleep(1/30)
        self.cam.release()