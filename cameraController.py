import cv2
from threading import Thread
import time
import common.settings as settings
import queue
from detect.motion import MotionDetect
import tornado.ioloop
from detect.scaleDetector import ScaleDetector


if settings.machine_state == "new":
    DEFAULT_WIDTH = 1280
    DEFAULT_HEIGHT = 720
else:
    DEFAULT_WIDTH = 640
    DEFAULT_HEIGHT = 480

DEFAULT_FPS = 20#视频文件的保存帧率，还需要和图像处理帧率进行比对

class VideoStream:
    def __init__(self,src,callback):
        self.src = src
        self.stream = cv2.VideoCapture(settings.usb_cameras[src])

        if settings.machine_state == "new":
            self.stream.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*'MJPG'))

        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH,DEFAULT_WIDTH)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT,DEFAULT_HEIGHT)
        self.call_back = callback
        self.isSending = False

        self.updateScheduler = tornado.ioloop.PeriodicCallback(self.update,5)
        self.updateScheduler.start()

        # self.cnt = 0
        self.motionChecker = MotionDetect()

    def update(self):
        if self.isSending:
            ret,frame = self.stream.read()
            if ret:
                centerX = settings.detect_baseLine[self.src]
                motionType = self.motionChecker.checkInput(frame[:,int(centerX)-10:int(centerX)+10],time.time())
                self.call_back(self.src,frame,motionType)

    def setSending(self,state):
        self.isSending = state
        if not state:
            self.motionChecker.reset()


class CameraController:
    def __init__(self,input_queue):
        self.cameras = {}
        self.frames_queues = input_queue
        self.videoWriter={}
        # self.cnt = 0
        # self.lastTime = time.time()
        for i in range(4):
            self.cameras[i] = VideoStream(i,self.sendFrame)

        if settings.has_scale:
            self.scaleDetector = ScaleDetector()

    def getScaleDetector(self):
        return self.scaleDetector

    def startCameras(self,cameras):
        self.curCameras = cameras
        for src in cameras:
            self.cameras[src].setSending(True)
            if settings.logger.checkSaveVideo():
                self.videoWriter[src] = cv2.VideoWriter(settings.logger.getSaveVideoPath()+str(src)+".avi", 
                    cv2.VideoWriter_fourcc(*'XVID'),DEFAULT_FPS, (DEFAULT_WIDTH,DEFAULT_HEIGHT))


    def stopCameras(self):
        for src in self.curCameras:
            self.cameras[src].setSending(False)
            if settings.logger.checkSaveVideo():
                self.videoWriter[src].release()


    def sendFrame(self,src,frame,motionType):
        if settings.has_scale:
            # self.scaleDetector[src%2].check(motionType)
            self.scaleDetector.check(motionType)

        try:
            # self.cnt+=1
            # cur=time.time()
            # if cur - self.lastTime>1.0:
            #     print("send ",self.cnt," frame cur second")
            #     self.cnt=0 
            #     self.lastTime = cur

            if settings.logger.checkSaveVideo():
                self.videoWriter[src].write(frame)

            if src > 1:
                frame = frame[:, :settings.detect_baseLine[src]+10]
            else:
                frame = frame[:, settings.detect_baseLine[src]-10:]

            settings.detect_baseLine[src]

            self.frames_queues.put((frame,src%2,time.time(),motionType))

        except queue.Full:
            settings.logger.info('[FULL] input_q')
            pass