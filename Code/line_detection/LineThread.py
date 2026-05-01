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
        
        self.detector = LineDetector()
        self.latestFrame = None
        self.latestIntersection = None
        self.roi = np.array([[self.roiKey["x1"], self.roiKey["y1"]], [self.roiKey["x2"], self.roiKey["y2"]], [self.roiKey["x3"], self.roiKey["y3"]], [self.roiKey["x4"], self.roiKey["y4"]]], np.int32)
        self.roiBounds = cv2.boundingRect(self.roi)
        self.A, self.B = self.getRoiLinePoints((self.lineKey["A"]["x"], self.lineKey["A"]["y"]), (self.lineKey["B"]["x"], self.lineKey["B"]["y"]))
        print(f"LineThread for {self.cam.camPos} initialized with ROI bounds: {self.roiBounds} and line points A: {self.A}, B: {self.B}")

    # dont try to simplify this, it just breaks somehow, and i have no idea why
    def toRoi(self, point, roi):
        x0, y0, _, _ = roi
        x, y = point
        return (x - x0, y - y0)

    def getRoiLinePoints(self, pointA, pointB):
        # Find all intersections of the line with ROI polygon edges and endpoints inside polygon
        poly = self.roi.reshape((-1, 2)).astype(np.float32)
        candidates = []
        
        # Check if endpoints are inside the polygon
        if cv2.pointPolygonTest(poly, pointA, False) >= 0:
            candidates.append(pointA)
        if cv2.pointPolygonTest(poly, pointB, False) >= 0:
            candidates.append(pointB)
        
        # Find intersections with polygon edges
        for i in range(len(poly)):
            edge_start = poly[i]
            edge_end = poly[(i + 1) % len(poly)]
            inter = self.lineSegmentIntersection(pointA, pointB, edge_start, edge_end)
            if inter is not None:
                candidates.append(inter)
        
        if len(candidates) < 2:
            return self.toRoi(pointA, self.roiBounds), self.toRoi(pointB, self.roiBounds)
        
        # Remove duplicates and sort along the line direction
        unique = []
        for p in candidates:
            if not any(np.linalg.norm(np.array(p) - np.array(u)) < 1e-3 for u in unique):
                unique.append(p)
        
        if len(unique) < 2:
            return self.toRoi(pointA, self.roiBounds), self.toRoi(pointB, self.roiBounds)
        
        # Sort by projection along line direction
        pa = np.array(pointA, dtype=np.float32)
        pb = np.array(pointB, dtype=np.float32)
        direction = pb - pa
        denom = np.dot(direction, direction)
        if denom < 1e-6:
            return self.toRoi(pointA, self.roiBounds), self.toRoi(pointB, self.roiBounds)
        
        unique.sort(key=lambda p: np.dot(np.array(p) - pa, direction) / denom)
        clippedA = tuple(map(int, unique[0]))
        clippedB = tuple(map(int, unique[-1]))
        
        return self.toRoi(clippedA, self.roiBounds), self.toRoi(clippedB, self.roiBounds)
    
    def lineSegmentIntersection(self, p1, p2, p3, p4):
        x1, y1 = np.array(p1, dtype=np.float32)
        x2, y2 = np.array(p2, dtype=np.float32)
        x3, y3 = np.array(p3, dtype=np.float32)
        x4, y4 = np.array(p4, dtype=np.float32)
        
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-6:
            return None
        
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        
        if 0 <= t <= 1 and 0 <= u <= 1:
            ix = x1 + t * (x2 - x1)
            iy = y1 + t * (y2 - y1)
            return (ix, iy)
        return None
    
    def applyRoi(self, frame):
        x, y, w, h = self.roiBounds
        roiFrame = frame[y:y+h, x:x+w]
        localRoi = self.roi - np.array([x, y])
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [localRoi.reshape((-1, 1, 2))], 255)
        maskedRoiFrame = cv2.bitwise_and(roiFrame, roiFrame, mask=mask)
        return roiFrame, maskedRoiFrame, mask, (x, y, w, h)

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            frame = self.cam.getFrame()
            # mask the frame to only include the roi, and also get the original roi frame for later use
            originalRoiFrame, roiFrame, mask, (x, y, w, h) = self.applyRoi(frame)

            # get the intersection of the line with the roi, and also get the processed roi frame for later use
            intersection, roiFrame = self.detector.getIntersection(roiFrame, self.A, self.B)
            
            # create a display frame that only shows the roi, and also draw the line and the intersection on it, and then put it back on the original frame
            displayRoiFrame = originalRoiFrame.copy()
            displayRoiFrame[mask == 255] = roiFrame[mask == 255]
            frame[y:y+h, x:x+w] = displayRoiFrame
            # outline the roi
            cv2.polylines(frame, [self.roi.reshape((-1, 1, 2))], True, (255, 0, 0), 2)
            # draw the detection line
            cv2.line(frame, (self.lineKey["A"]["x"],self.lineKey["A"]["y"]), (self.lineKey["B"]["x"],self.lineKey["B"]["y"]), (0,0,255), 2)
            
            cv2.line(frame, (x + self.A[0], y + self.A[1]), (x + self.B[0], y + self.B[1]), (255,255,0), 2)
            
            self.latestFrame = frame
            self.latestIntersection = intersection
            time.sleep(1/30)
        self.cam.release()