#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cv2
import queue
from threading import Thread
import time
import signal
import settings
from setproctitle import setproctitle
import settings

DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480
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
        self.stream = cv2.VideoCapture(settings.usb_cameras[src])
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        (self.grabbed, self.frame) = self.stream.read()

        # initialize the variable used to indicate if the thread should
        # be stopped
        self.stopped_caching = False
        self.sending_frame = False

        

    def start(self):
        # start the thread to read frames from the video stream
        Thread(target=self.update, args=()).start()
        return self

    def update(self):
        while not self.stopped_caching:
            (self.grabbed, self.frame) = self.stream.read()

    def read(self):
        return self.frame

    def reset(self):
        self.frame = None

    def stop(self):
        self.stopped_caching = True

    def pause_sending(self):
        self.sending_frame = False

    def resume_sending(self):
        self.sending_frame = True


class CameraHandler:
    '''
        工作在一个单独进程中，通过 ctrl_q 接受控制命令，决定是否把摄像头产生的图像发送到输出队列中
    '''
    IDLE_TIMEOUT = 1
    BUSY_TIMEOUT = 0.01

    def __init__(self, ctrl_q, frames_queues, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
        self.ctrl_q = ctrl_q
        self.frames_queues = frames_queues
        self.timeout = CameraHandler.BUSY_TIMEOUT
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

        # print("reset is save ahtne")
        for i in range(4):
            self.isSave[i] = False

        # self.calcTime = time.time()
        # self.calc_cnt = 0

    def start(self):
        # 忽略 SIGINT，由父进程处理
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        setproctitle('[farsight] sending process of camera')
        
        while True:
            try:
                ctrl_data = self.ctrl_q.get(timeout=self.timeout)
                self._handle_command(ctrl_data['cmd'], ctrl_data['cameras'])
            except queue.Empty:
                # print('[EMPTY] ctrl_q')
                pass

            for src in self.cameras.keys():
                if self.cameras[src].sending_frame:
                    self._sendframe(src)

    def _handle_command(self, cmd, cameras):
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
            # print("Cameras are:   ",cameras)
            for src in cameras:
                self.cameras[src].resume_sending()
                if settings.SAVE_VIDEO_OUTPUT:
                    video_FileName =  './Output/Video__'\
                                    + time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime( time.time() ) )\
                                    + '__'\
                                    + str(src)\
                                    + '.avi'             
                    self.videoWriter[src] = cv2.VideoWriter(video_FileName, cv2.VideoWriter_fourcc(*'XVID')
                                        , DEFAULT_FPS, (DEFAULT_WIDTH,DEFAULT_HEIGHT))#每个启动的摄像头有一个保存类
        elif cmd == 'stop':
            for src in cameras:
                self.cameras[src].pause_sending()
                if settings.SAVE_VIDEO_OUTPUT:
                    del self.videoWriter[src]  # 摄像头停止活动后销毁视频保存类
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
            data = self.cameras[src].read()#after fetching,
            # print("send frame src is: ",src)
            # self.frames_queues[src].put((data,src), timeout=1)
            if data is not None:
                self.frames_queues.put((data,src,time.time()), timeout=1)

                # self.calc_cnt +=1
                # if time.time() - self.calcTime > 1:
                #     # print(self.calc_cnt," frame sent every second")
                #     self.calcTime = time.time()
                #     self.calc_cnt = 0
                #     return

                if settings.SAVE_VIDEO_OUTPUT:
                    self.videoWriter[src].write(data)  # 将每一帧写入视频文件中

                if settings.SAVE_DEBUG_OUTPUT and not self.isSave[src]:
                    self.isSave[src] = True
                    tiem = time.time()
                    # cv2.imwrite("Output/"+str(src)+"_"+str(tiem)+".png",data)
                      # 将每一帧写入视频文件中
                    # slide = data[:,310:330]
                    # cv2.imwrite("Output/slide"+str(src)+"_"+str(tiem)+".png",slide)

            self.cameras[src].reset()

        except queue.Full:
            print('[FULL] input_q')
            pass


if __name__ == '__main__':
    setproctitle('[farsight] main process')

    from multiprocessing import Queue, Process
    ctrl_q = Queue(1)
    frames_queues = [Queue(5)]
    cam_handler = CameraHandler(ctrl_q, frames_queues)
    process = Process(target=cam_handler.start)
    process.start()

    import sys

    class SignalHandler:
        def __init__(self, process):
            self.process = process

        def signal_handler(self, signal, f):
            self.process.terminate()
            sys.exit(0)

    sig_handler = SignalHandler(process)

    signal.signal(signal.SIGINT, sig_handler.signal_handler)

    ctrl_q.put(dict(cmd='standby', cameras=[0]))
    ctrl_q.put(dict(cmd='start', cameras=[0]))
    time.sleep(3)
    ctrl_q.put(dict(cmd='stop', cameras=[0]))
    # while True:
    #     pass
