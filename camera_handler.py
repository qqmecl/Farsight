import cv2
from threading import Thread
import time
import common.settings as settings
import queue
import tornado.ioloop
# from multiprocessing import Queue, Process

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_FPS = 25#视频文件的保存帧率，还需要和图像处理帧率进行比对

class VideoStream:
    def __init__(self,src,callback):
        self.src = src
        self.stream = cv2.VideoCapture(settings.usb_cameras[src])
        self.stream.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*'MJPG'))
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH,DEFAULT_WIDTH)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT,DEFAULT_HEIGHT)
        self.call_back = callback
        self.isSending = False

        self.updateScheduler = tornado.ioloop.PeriodicCallback(self.update,5)#100 fps
        self.updateScheduler.start()

        self.last = time.time()
        self.cnt = 0

    def update(self):
        if self.isSending:
            self.cnt+=1
            cur = time.time()
            if cur-self.last >1.0:
                print(self.cnt," update every second for ",self.src)
                self.last = cur
                self.cnt=0

            ret,frame = self.stream.read()
            if ret:
                self.call_back(self.src,frame)

    def setSending(self,state):
        self.isSending = state
        
class CameraController:
    def __init__(self,input_queue):
        self.cameras = {}
        self.frames_queues = input_queue

        self.cnt = 0
        self.lastTime = time.time()
        self.count = 0
        self.videoWriter = {}

        for i in range(4):
            self.cameras[i] = VideoStream(i,self.sendFrame)
        
    def startCameras(self,cameras):
        self.curCameras = cameras
        for src in cameras: 
            if settings.logger.checkSaveVideo():
                self.videoWriter[src] = cv2.VideoWriter(settings.logger.getSaveVideoPath()+str(src)+".avi", cv2.VideoWriter_fourcc(*'XVID')
                                        , DEFAULT_FPS, (DEFAULT_WIDTH,DEFAULT_HEIGHT))#每个启动的摄像头有一个保存类

            self.cameras[src].setSending(True)

    def stopCameras(self):
        for src in self.curCameras:
            self.cameras[src].setSending(False)

        if settings.logger.checkSaveVideo():
            self.videoWriter[src].release()

    def sendFrame(self,src,frame):
        try:
            self.count +=1
            if src > 1:
                frame = cv2.flip(frame,1)
            # self.cnt += 1
            # if time.time() - self.lastTime > 1:
            #     print("send ",self.cnt," frame cur second")
            #     self.cnt=0 
            #     self.lastTime = time.time()

            # if self.count % 2 and self.count % 3 and self.count % 5:
            if not self.count % 3:
                # print(self.count)
                self.frames_queues.put((frame, src % 2, time.time()))
                # self.cnt += 1
                # if time.time() - self.lastTime > 1:
                #     print("send ",self.cnt," frame cur second")
                #     self.cnt=0 
                #     self.lastTime = time.time()
            
            if settings.logger.checkSaveVideo():
                self.videoWriter[src].write(frame)
        except queue.Full:
            settings.logger.info('[FULL] input_q')
            pass