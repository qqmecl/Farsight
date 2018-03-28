import cv2
import time

usb_cameras = [
"/dev/v4l/by-path/pci-0000:00:14.0-usb-0:1:1.0-video-index0",
"/dev/v4l/by-path/pci-0000:00:14.0-usb-0:3:1.0-video-index0",
"/dev/v4l/by-path/pci-0000:00:14.0-usb-0:2:1.0-video-index0",
"/dev/v4l/by-path/pci-0000:00:14.0-usb-0:4:1.0-video-index0"]


camera =cv2.VideoCapture(usb_cameras[0])
# 
w,h = 1280, 720
# w,h = 640,480
# w,h =  640*1.2,480*1.2
# w,h =  w/2,h/2
w,h = int(w),int(h)
camera.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*'MJPG'))
camera.set(cv2.CAP_PROP_FRAME_WIDTH,w)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT,h)

last = time.time()
cnt=0

while True:
    (grabbed, frame) = camera.read()

    cnt+=1
    now = time.time()

    if now-last>1.0:
        last = now
        print(cnt)
        cnt=0
    cv2.imshow("img", frame)

    key = cv2.waitKey(1) & 0xff