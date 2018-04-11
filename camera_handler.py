import cv2
from threading import Thread
import time
import common.settings as settings
import queue
from detect.motion import MotionDetect
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

        self.updateScheduler = tornado.ioloop.PeriodicCallback(self.update,5)
        self.updateScheduler.start()

        self.last = time.time()
        self.cnt = 0
        self.motionChecker = MotionDetect()

    def update(self):
        if self.isSending:
            self.cnt+=1
            ret,frame = self.stream.read()
            if ret:
                self.cnt+=1
                if self.cnt == 99:
                    self.cnt = 0

                motionType = self.motionChecker.checkInput(frame[:,630:650],time.time())
                if self.cnt %3 == 0 or motionType != "None":

                    self.call_back(self.src,frame,motionType)

    def setSending(self,state):
        self.isSending = state
        
# class CameraController:
#     def __init__(self,input_queue):
#         self.cameras = {}
#         self.frames_queues = input_queue

#         self.cnt = 0
#         self.lastTime = time.time()
#         self.count = 0
#         self.videoWriter = {}
#         self.motions = []
#         self.motion_result = "None"
#         self.push_time = None
#         self.pull_time = None
#         self.motion_sign = 0


#         for i in range(2):
#             self.motions.append(MotionDetect(i))

#         for i in range(4):
#             self.cameras[i] = VideoStream(i,self.sendFrame)
        
#     def startCameras(self,cameras):
#         self.curCameras = cameras
#         for src in cameras: 
#             if settings.logger.checkSaveVideo():
#                 self.videoWriter[src] = cv2.VideoWriter(settings.logger.getSaveVideoPath()+str(src)+".avi", cv2.VideoWriter_fourcc(*'XVID')
#                                         , DEFAULT_FPS, (DEFAULT_WIDTH,DEFAULT_HEIGHT))#每个启动的摄像头有一个保存类

#             self.cameras[src].setSending(True)
#             self.motion_sign = 1

#     def stopCameras(self):
#         for src in self.curCameras:
#             self.cameras[src].setSending(False)

#         for i in range(2):
#             self.motions[i].reset()

#         if settings.logger.checkSaveVideo():
#             self.videoWriter[src].release()

#         self.motion_sign = 0

#     def sendFrame(self,src,frame):
#         try:
#             self.count +=1
#             if src > 1:
#                 frame = cv2.flip(frame,1)
#             # self.cnt += 1
#             # if time.time() - self.lastTime > 1:
#             #     print("send ",self.cnt," frame cur second")
#             #     self.cnt=0 
#             #     self.lastTime = time.time()

#             checkIndex = src % 2
#             frame_time = time.time()

#             if self.motion_sign:
#                 # self.cnt += 1
#                 # if time.time() - self.lastTime > 1:
#                 #     print("send ",self.cnt," frame cur second")
#                 #     self.cnt=0 
#                 #     self.lastTime = time.time()
#                 motionType = self.motions[checkIndex].checkInput(frame[:,630:650],frame_time)
#                 # print(motionType)
#                 if motionType:
#                     self.motion_result = motionType
#                     self.push_time = self.motions[checkIndex].getMotionTime("PUSH")
#                     self.pull_time = self.motions[checkIndex].getMotionTime("PULL")

#             # if self.count % 2 and self.count % 3 and self.count % 5:
#             if not self.count % 3:
#                 # print(self.count)
#                 self.frames_queues.put((frame, checkIndex, frame_time, self.motion_result, self.push_time, self.pull_time))
#                 self.motion_result = "None"
#                 # self.push_time = None
#                 # self.pull_time = None
#                 # self.cn`= time.time()
            
#             if settings.logger.checkSaveVideo():
#                 self.videoWriter[src].write(frame)
#         except queue.Full:
#             settings.logger.info('[FULL] input_q')
#             pass


class CameraController:
    def __init__(self,input_queue):
        self.cameras = {}
        self.frames_queues = input_queue
        self.videoWriter={}
        # self.cnt = 0
        # self.lastTime = time.time()
        for i in range(4):
            self.cameras[i] = VideoStream(i,self.sendFrame)


    def startCameras(self,cameras):
        self.curCameras = cameras
        for src in cameras:
            self.cameras[src].setSending(True)
            if settings.logger.checkSaveVideo():
                self.videoWriter[src] = cv2.VideoWriter(settings.logger.getSaveVideoPath()+str(src)+".avi", cv2.VideoWriter_fourcc(*'XVID'),20, (DEFAULT_WIDTH,DEFAULT_HEIGHT))

    def stopCameras(self):
        for src in self.curCameras:
            self.cameras[src].setSending(False)
            if settings.logger.checkSaveVideo():
                self.videoWriter[src].release()

    def sendFrame(self,src,frame,motionType):
        try:
            # cur=time.time()
            # if cur - self.lastTime>1.0:
                # print("send ",self.cnt," frame cur second")
                # self.cnt=0 
                # self.lastTime = cur
            if settings.logger.checkSaveVideo():
                self.videoWriter[src].write(frame)

            if src > 1:
                frame = cv2.flip(frame,1)
                    
            if src%2 == 1:
                frame = frame[:, 160: , :]#Camera downstairs
            else:
                frame = frame[:, 260: , :]#Camera upstairs
            self.frames_queues.put((frame,src%2,time.time(),motionType))

        except queue.Full:
            settings.logger.info('[FULL] input_q')
            pass