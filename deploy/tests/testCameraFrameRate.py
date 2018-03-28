import cv2 
import numpy as np
import time

#fileName="../../data/input/live_video/live/1.avi"
camera=cv2.VideoCapture(0) 
firstframe=None
frameCount = 0

lastTime = time.time()
total=0
while True:
  ret,frame = camera.read()
  if not ret: 
    break
  frameCount+=1
  total+=1

  nowTime = time.time()
  if (nowTime-lastTime >= 1.0):
    print("Frame rate: ",frameCount)
    lastTime = nowTime
    frameCount=0

  cv2.imshow("frame", frame)

  # cv2.imwrite("www"+str(frameCount)+".png",frame)
  
  key = cv2.waitKey(1)&0xFF
    
  if key == ord("q"):
    break

print("final cnt is: ",total)

camera.release()
cv2.destroyAllWindows()