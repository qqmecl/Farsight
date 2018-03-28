#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cv2
import queue
from threading import Thread
import time
import signal
from setproctitle import setproctitle
import common.settings as settings

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_FPS = 25 # 视频文件的保存帧率，还需要和图像处理帧率进行比对

class WebcamVideoStream:
    '''
        源自 https://github.com/datitran/object_detector_app
        在一个线程中不断获取摄像头的输出并且缓存下来，大幅提高帧率
    '''
    def __init__(self, src, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
        # initialize the video camera stream and read the first frame
        # from the stream
        self.src = src
        self.width = width
        self.height = height
        self.stream = cv2.VideoCapture(settings.usb_cameras[src])
        #w,h = 1280, 720
        # w,h = 640,480
        # w,h =  640*1.2,480*1.2
        # w,h =  w/2,h/2
        #w,h = int(w),int(h)
        self.stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        # (self.grabbed, self.frame) = self.stream.read()
        # initialize the variable used to indicate if the thread should
        # be stopped
        self.stopped_caching = True
        self.reset()

    def start(self):
        # start the thread to read frames from the video stream
        Thread(target=self.update, args=()).start()
        return self

    def update(self):
        while True:
            if not self.stopped_caching:
                (self.grabbed, self.frame) = self.stream.read()

    def read(self):
        return self.frame

    def reset(self):
        self.frame = None

    def pause_sending(self):
        self.stopped_caching = True
        # self.stream.release()
        
    def resume_sending(self):
        # self.stream = cv2.VideoCapture(settings.usb_cameras[self.src])
        # self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        # self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.stopped_caching = False

class CameraHandler:
    '''
        工作在一个单独进程中，通过 ctrl_q 接受控制命令，决定是否把摄像头产生的图像发送到输出队列中
    '''
    def __init__(self, ctrl_q, frames_queues, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
        self.ctrl_q = ctrl_q
        self.frames_queues = frames_queues
        self.timeout = 0.01
        self.cameras = {}
        self.videoWriter = {}
        self.isSave=[]
        for i in range(4):
            self.isSave.append(False)
        self.reset()

    def reset(self):
        while True:#empty input frame queue
            try:
                frame = self.frames_queues.get_nowait()
            except queue.Empty:
                break

        # settings.logger.info("reset is save ahtne")
        for i in range(4):
            self.isSave[i] = False

        # self.calcTime = time.time()
        # self.calc_cnt = 0

    def start(self):
        # 忽略 SIGINT，由父进程处理
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        setproctitle('[farsight] 摄像头发送帧进程')
        
        while True:
            try:
                ctrl_data = self.ctrl_q.get(timeout=self.timeout)
                self._handle_command(ctrl_data['cmd'], ctrl_data['cameras'],ctrl_data['videoPath'])
            except queue.Empty:
                # settings.logger.info('[EMPTY] ctrl_q')
                pass

            for src in self.cameras.keys():
                self._sendframe(src)

    def _handle_command(self, cmd, cameras,videoPath):
        '''
            cmd 参数是指令名称，cameras 是摄像头编号
            根据指令类型，让参数对应的摄像头进入相应的状态
            standby: 启动摄像头，进入待命状态
            start:   发送摄像头捕获的帧到队列中
            stop:    停止发送帧
        '''
        if cmd == 'standby':#主程序第一次运行时，摄像头启动，不考虑之后动态变化
            for src in cameras:
                self.cameras[src] = WebcamVideoStream(src)
                self.cameras[src].start()
        elif cmd == 'start':#打开门之后算法进程才有数据进行检测
            for src in cameras:
                self.cameras[src].resume_sending()

                if settings.logger.checkSaveVideo():
                    self.videoWriter[src] = cv2.VideoWriter(videoPath+str(src)+".avi", cv2.VideoWriter_fourcc(*'XVID')
                                        , DEFAULT_FPS, (DEFAULT_WIDTH,DEFAULT_HEIGHT))#每个启动的摄像头有一个保存类
        elif cmd == 'stop':
            for src in cameras:
                self.cameras[src].pause_sending()
                if settings.logger.checkSaveVideo():
                    if not self.cameras[src].stopped_caching:
                        del self.videoWriter[src]  #摄像头停止活动后销毁视频保存类
            self.reset()

    def _sendframe(self, src):
        '''
            发送摄像头图像帧到对应的队列中
            TODO:
            当个别摄像头对应的 TensorFlow 处理进程处理较慢时，可能出现队列满的情况，
            此时可能导致其他队列的发送也被 block 住
            考虑调低 timeout 或者使用后台线程
        '''
        try:
            data = self.cameras[src].read()
            if data is not None:
                self.frames_queues.put((data,src,time.time()), timeout=1)

                # self.calc_cnt +=1
                # if time.time() - self.calcTime > 1:
                #     print(self.calc_cnt," frame sent every second")
                #     # settings.logger.info(self.calc_cnt," frame sent every second")
                #     self.calcTime = time.time()
                #     self.calc_cnt = 0
                #     return

                if settings.logger.checkSaveVideo():
                    self.videoWriter[src].write(data)  # 将每一帧写入视频文件中

                if settings.SAVE_DEBUG_OUTPUT and not self.isSave[src]:
                    self.isSave[src] = True
                    tiem = time.time()

                self.cameras[src].reset()
        except queue.Full:
            settings.logger.info('[FULL] input_q')
            pass