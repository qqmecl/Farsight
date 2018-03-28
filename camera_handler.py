import cv2
import queue
from threading import Thread
import time
import signal
from setproctitle import setproctitle
import common.settings as settings
from detect.dynamic_track import DynamicTrack


DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480
DEFAULT_FPS = 25#视频文件的保存帧率，还需要和图像处理帧率进行比对

class WebcamVideoStream:
    def __init__(self, src, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
        self.src = src
        self.width = width
        self.height = height
        self.stream = cv2.VideoCapture(settings.usb_cameras[src])
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.stopped_caching = True
        self.reset()

    def start(self):
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
        
    def resume_sending(self):
        self.stopped_caching = False


class CameraHandler:
    def __init__(self, ctrl_q, frames_queues, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
        self.ctrl_q = ctrl_q
        self.frames_queues = frames_queues
        self.timeout = 0.01
        self.cameras = {}
        self.videoWriter = {}
        self.dynamicTracker= {}
        for i in range(4):
            self.dynamicTracker[i] = DynamicTrack()

        self.reset()

    def reset(self):
        while True:
            try:
                frame = self.frames_queues.get_nowait()
            except queue.Empty:
                break

    def start(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        setproctitle('[farsight] 摄像头发送帧进程')
        while True:
            try:
                ctrl_data = self.ctrl_q.get(timeout=self.timeout)
                self._handle_command(ctrl_data['cmd'], ctrl_data['cameras'],ctrl_data['videoPath'])
            except queue.Empty:
                pass

            for src in self.cameras.keys():
                self._sendframe(src)


    def _handle_command(self, cmd, cameras,videoPath):
        if cmd == 'standby':#主程序第一次运行时，摄像头启动，不考虑之后动态变化
            for src in cameras:
                self.cameras[src] = WebcamVideoStream(src)
                self.cameras[src].start()
        elif cmd == 'start':#打开门之后算法进程才有数据进行检测
            for src in cameras:
                self.cameras[src].resume_sending()
                if settings.logger.checkSaveVideo():
                    self.videoWriter[src] = cv2.VideoWriter(videoPath+str(src)+".avi", cv2.VideoWriter_fourcc(*'XVID'),DEFAULT_FPS,(DEFAULT_WIDTH,DEFAULT_HEIGHT))#每个启动的摄像头有一个保存类
        
        elif cmd == 'stop':
            for src in cameras:
                self.cameras[src].pause_sending()
                if settings.logger.checkSaveVideo():
                    if not self.cameras[src].stopped_caching:
                        del self.videoWriter[src] #摄像头停止活动后销毁视频保存类
            self.reset()


    def _sendframe(self, src):
        try:
            data = self.cameras[src].read()
            data = self.dynamicTracker[src].check(data)
            if data is not None:
                self.frames_queues.put((data,src,time.time()), timeout=1)

                if settings.logger.checkSaveVideo():#将每一帧写入视频文件中
                    self.videoWriter[src].write(data)

                self.cameras[src].reset()

        except queue.Full:
            settings.logger.info('[FULL] input_q')
            pass