from line_detection.LineDetector import LineDetector
import numpy as np
import threading
import time
import json
import cv2
import os

class LineThread(threading.Thread):
    def __init__(self, cam):
        threading.Thread.__init__(self)
        with open(os.path.join(os.path.dirname(__file__), '..', 'config.json'), 'r') as file:
            self.config = json.load(file)
        
        self.cam = cam
        
        self.roiKey = self.config[f"{self.cam.camPos}Roi"]
        self.lineKey = self.config[f"{self.cam.camPos}DiagonalLine"]
        
        self.running = True
        
        # synchronization primitives for coordinated frame reads
        self._cond = threading.Condition()
        self.latestIndex = 0

        # when True, the thread will wait for a step request from the controller
        self.sync_mode = False
        self._step_requested = False
        
        self.latestFrame = None
        self.latestIntersection = None
        # self.brokenLine = False
        # self.lastHitTime = 0.0
        # self.breakThreshold = 0.7
        # self.lineThreshold = 4.0

        self.roi = np.array([[self.roiKey["x1"], self.roiKey["y1"]], [self.roiKey["x2"], self.roiKey["y2"]], [self.roiKey["x3"], self.roiKey["y3"]], [self.roiKey["x4"], self.roiKey["y4"]]], np.int32)
        self.roiBounds = cv2.boundingRect(self.roi)
        self.A = self.toRoi((self.lineKey["A"]["x"], self.lineKey["A"]["y"]), self.roiBounds)
        self.B = self.toRoi((self.lineKey["B"]["x"], self.lineKey["B"]["y"]), self.roiBounds)
        if self.cam.camPos == "left":
            self.detector = LineDetector(np.sqrt((self.lineKey["B"]["x"] - self.lineKey["A"]["x"])**2 + (self.lineKey["B"]["y"] - self.lineKey["A"]["y"])**2), self.A, self.B, True)
        else:
            self.detector = LineDetector(np.sqrt((self.lineKey["B"]["x"] - self.lineKey["A"]["x"])**2 + (self.lineKey["B"]["y"] - self.lineKey["A"]["y"])**2), self.A, self.B, False)

    # dont try to simplify this, it just breaks somehow, and i have no idea why
    def toRoi(self, point, roi):
        x0, y0, _, _ = roi
        x, y = point
        return (x - x0, y - y0)
    
    def applyRoi(self, frame):
        x, y, w, h = self.roiBounds
        roiFrame = frame[y:y+h, x:x+w]
        localRoi = self.roi - np.array([x, y])
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [localRoi.reshape((-1, 1, 2))], 255)
        maskedRoiFrame = cv2.bitwise_and(roiFrame, roiFrame, mask=mask)
        return roiFrame, maskedRoiFrame, mask, (x, y, w, h)

    def stop(self):
        # stop thread and notify any waiters and step requests
        if self.sync_mode:
            with self._cond:
                self.running = False
                self._step_requested = True
                self._cond.notify_all()
        else:
            self.running = False

    def enable_sync_mode(self, enable=True):
        """Enable or disable step-based synchronous processing."""
        with self._cond:
            self.sync_mode = bool(enable)
            # wake thread so it can notice mode change
            self._cond.notify_all()

    def request_step(self):
        """Request the thread to process exactly one frame (only in sync_mode)."""
        with self._cond:
            if not self.running:
                return
            self._step_requested = True
            self._cond.notify_all()

    def wait_for_index(self, prev_index, timeout=None):
        """Block until the internal frame index advances past prev_index or timeout.
        Returns the new latestIndex (may be unchanged on timeout/stop).
        """
        with self._cond:
            end = None
            if timeout is not None:
                end = time.time() + timeout
            while self.latestIndex == prev_index and self.running:
                remaining = end - time.time() if end is not None else None
                if remaining is not None and remaining <= 0:
                    break
                self._cond.wait(timeout=remaining)
            return self.latestIndex
        
    # def checkForBrokenLine(self):
    #     currentTime = time.time()
    #     if currentTime - self.lastHitTime >= self.breakThreshold:
    #         self.brokenLine = True
        
    #     if currentTime - self.lastHitTime >= self.lineThreshold:
    #         self.brokenLine = False

    def run(self):
        while self.running:
            # if in sync mode, wait until a step is requested
            if self.sync_mode:
                with self._cond:
                    while not self._step_requested and self.running:
                        self._cond.wait()
                    if not self.running:
                        break
                    # consume the step request and proceed
                    self._step_requested = False
            
            frame = self.cam.getFrame()
            # mask the frame to only include the roi, and also get the original roi frame for later use
            originalRoiFrame, roiFrame, mask, (x, y, w, h) = self.applyRoi(frame)

            # get the intersection of the line with the roi, and also get the processed roi frame for later use
            intersection, roiFrame = self.detector.getIntersection(roiFrame, self.A, self.B)
            
            # create a display frame that only shows the roi, and also draw the line and the intersection on it, and then put it back on the original frame
            displayRoiFrame = originalRoiFrame.copy()
            displayRoiFrame[mask == 255] = roiFrame[mask == 255]
            frame[y:y+h, x:x+w] = displayRoiFrame
            
            # outline the roi, blue
            cv2.polylines(frame, [self.roi.reshape((-1, 1, 2))], True, (255, 0, 0), 2)
            
            # draw the detection line, red
            cv2.line(frame, (self.lineKey["A"]["x"],self.lineKey["A"]["y"]), (self.lineKey["B"]["x"],self.lineKey["B"]["y"]), (0,0,255), 2)
        
            # update latest data and notify any waiters
            if self.sync_mode:
                with self._cond:
                    self.latestFrame = frame
                    self.latestIntersection = intersection
                    self.latestIndex += 1
                    self._cond.notify_all()
            else:
                self.latestFrame = frame
                self.latestIntersection = intersection
                
            # if intersection is not None:
            #     self.lastHitTime = time.time()
            # self.checkForBrokenLine()
            # print(f"LineThread {self.cam.camPos} / Broken: {self.brokenLine} / LastHitTime {self.lastHitTime}", flush=True)
            time.sleep(1/30)
        self.cam.release()