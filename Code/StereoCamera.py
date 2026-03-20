from abc import ABC
import numpy as np
import cv2

class StereoCamera(ABC):
	def __init__(self, index, camPos):
		self.cam = cv2.VideoCapture(index, cv2.CAP_V4L2)
		if not self.cam.isOpened():
			print(f"Camera {index} failed to open")
			return None
		self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
		self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
		self.cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'mp4v'))
		self.cam.set(cv2.CAP_PROP_FPS, 30)
		self.cam.set(cv2.CAP_PROP_AUTOFOCUS, 0)
		self.camPos = camPos
		self.index = index
		
		fourcc = cv2.VideoWriter_fourcc(*'mp4v')
		self.writer = cv2.VideoWriter(
			f"{self.camPos}.mp4",
			fourcc,
			30,
			(1280, 720)
		)
		print(f"Stereo Camera {index} initialized.")
		
	def getFrame(self):
		ret, frame = self.cam.read()
		if not ret:
			print("Failed to grab frame")
			return None
		return frame

class LineStereoCamera(StereoCamera):    
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
		
		filteredFrame = cv2.inRange(filteredFrame, 195, 255)

		# filter between dark and light and make dark black and light white
		_, filteredFrame = cv2.threshold(filteredFrame, 200, 255, cv2.THRESH_BINARY)

		kernel1 = np.array([[100, 5, 100],[5, 100, 5],[100, 5, 100]])

		filteredFrame = cv2.filter2D(filteredFrame, -1, kernel1)

		# apply canny edge detection to see edges of objects
		filteredFrame = cv2.Canny(filteredFrame, threshold1=100, threshold2=150)
		height, width, _ = frame.shape

		kernel2 = np.ones((2,2), np.uint8)

		filteredFrame = cv2.morphologyEx(filteredFrame,cv2.MORPH_DILATE, kernel2)

		intersections = []

		lines = cv2.HoughLinesP(filteredFrame,1,np.pi/180,120,minLineLength=80,maxLineGap=50)
		if lines is not None:
			for line in lines:
				x1,y1,x2,y2 = line[0]
				cv2.line(frame,(x1,y1),(x2,y2),(0,0,255),2)  
				intersection = self.intersect((x1,y1), (x2,y2), (int(width/2),0), (int(width/2),height))
				if intersection is not None:				
					intersections.append(intersection)

		if intersections is not None and len(intersections) >= 2:
			lowest_intersection = max(intersections)
			cv2.circle(frame, lowest_intersection, 10, (255,0,0), -1)
		elif len(intersections) != 0:
			cv2.circle(frame, intersections[0], 10, (255,0,0), -1)
		
		cv2.line(frame,(int(width/2),0),(int(width/2),height),(255,255,0),2)

		# cv2.imshow(self.camPos, frame)
		return frame

class ObjectStereoCamera(StereoCamera):
	def processFrame(self, frame):
		return frame