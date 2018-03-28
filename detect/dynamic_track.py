import cv2
import numpy as np

# import time

class DynamicTrack:
    def __init__(self):
        self.lastFrame = None

    def check(self,frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.lastFrame is None:
            self.lastFrame = gray
            return None

        first_delta = cv2.absdiff(self.lastFrame,gray)
        ret,thresh =cv2.threshold(first_delta,10,255,cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 20))
        thresh = cv2.dilate(thresh, kernel)
        (_, cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        MaxC,maxArea = None,0

        self.lastFrame = gray

        for c in cnts:
            area = cv2.contourArea(c)
            if area > 8000 and area > maxArea:
                maxArea = 0
                MaxC = c
                
        if MaxC is not None:
            (x, y, w, h) = cv2.boundingRect(MaxC)
            imgROI = img[y:y + h, x:x + w]
            return imgROI
        return None