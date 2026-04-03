import cv2
import numpy as np

class LineDetector():
    def __init__(self):
        pass

    def cross(self, a, b):
        return a[0]*b[1] - a[1]*b[0]
    
    def intersect(self, A, B, x, y):
        if A[0] <= x <= B[0] or A[0]>= x >= B[0]:
            if A[0] == B[0]:
                return None
            a = (B[1]-A[1])/(B[0]-A[0])
            b = A[1] - a*A[0]
            if 0 <= a*x + b <= y:
                return (x, int(a*x + b))
        return None

    def processFrame(self, frame):
        # apply gaussian blur for less noise on the frame
        filteredFrame = cv2.GaussianBlur(frame, (15, 15), 1.4)

        # Turn the frame gray
        filteredFrame = cv2.cvtColor(filteredFrame, cv2.COLOR_BGR2GRAY)

        # filter between dark and light and make dark black and light white
        _, filteredFrame = cv2.threshold(filteredFrame, 200, 255, cv2.THRESH_BINARY)

        kernel = np.array([[10, 5, 10],[5, 10, 5],[10, 5, 10]])
        dst = cv2.filter2D(filteredFrame, -1, kernel)
        # cv2.imshow("zwartwit", dst)
        return dst
    
    def getIntersection(self, frame):
        intersections = []
        lines = cv2.HoughLinesP(self.processFrame(frame), 1, np.pi/180, 120, minLineLength=80, maxLineGap=50)
        height, width, _ = frame.shape
        if lines is not None:
            for line in lines:  
                x1,y1,x2,y2 = line[0]  
                cv2.line(frame,(x1,y1),(x2,y2),(0,0,255),2)
                intersection = self.intersect((x1,y1), (x2,y2), int(width/2), height)
                if intersection is not None:    
                    intersections.append(intersection)

        cv2.line(frame,(int(width/2),0),(int(width/2),height),(255,255,0),2)
        cv2.line(frame,(0,135),(639,135),(100,10,200),2)    
        if intersections is not None and len(intersections) >= 2:
            lowest_intersection = max(intersections,)
            cv2.circle(frame, lowest_intersection, 10, (255,0,0), -1)
            return (lowest_intersection, frame)
        elif len(intersections) != 0:
            cv2.circle(frame, intersections[0], 10, (255,0,0), -1)
            return (intersections[0], frame)
        return (None, frame)