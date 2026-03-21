import cv2
import numpy as np

class LineDetector():
    def __init__(self):
        pass

    def cross(self, a, b):
        return a[0]*b[1] - a[1]*b[0]

    def intersect (self, A, B, C, D):
        r = (B[0]-A[0], B[1]-A[1])
        s = (D[0]-C[0], D[1],C[1])
        CA = (C[0]-A[0], C[1]-A[1])

        denom = self.cross(r, s)
        if denom == 0:
            return None
        
        t = self.cross(CA, s) / denom
        u = self.cross(CA, r) / denom

        if 0 <= t <= 1 and 0  <= u <= 1:
            return (int(A[0] + t*r[0]), int(A[1] + t*r[1]))
        return None

    def processFrame(self, frame):
        # apply gaussian blur for less noise on the frame
        filteredFrame = cv2.GaussianBlur(frame, (15, 15), 1.4)

        # Turn the frame gray
        filteredFrame = cv2.cvtColor(filteredFrame, cv2.COLOR_BGR2GRAY)

        # filter between dark and light and make dark black and light white
        _, filteredFrame = cv2.threshold(filteredFrame, 200, 255, cv2.THRESH_BINARY)

        kernel = np.array([[100, 5, 100],[5, 100, 5],[100, 5, 100]])
        dst = cv2.filter2D(filteredFrame, -1, kernel)
        return dst
    
    def detectLines(self, frame):
        proccessedFrame = self.processFrame(frame)
        return cv2.HoughLinesP(proccessedFrame, 1, np.pi/180, 120, minLineLength=80, maxLineGap=50)
    
    def getIntersection(self, frame):
        intersections = []
        lines = self.detectLines(frame)
        for line in lines:
            height, width, _ = frame.shape
            x1,y1,x2,y2 = line[0]  
            intersection = self.intersect((x1,y1), (x2,y2), (int(width/2),0), (int(width/2),height))
            if intersection is not None:                
                intersections.append(intersection)
        
        if intersections is not None and len(intersections) >= 2:
            return max(intersections)
        elif len(intersections) != 0:
            return intersections[0]
        return None