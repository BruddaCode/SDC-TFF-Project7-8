import numpy as np
import cv2

class StereoCamera():
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