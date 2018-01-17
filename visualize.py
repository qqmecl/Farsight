import cv2
import queue
import tornado
import os
import numpy as np


class VisualizeDetection:
    '''
        开发过程中的可视化辅助程序，把物品识别的结果试试显示在屏幕上
    '''
    def __init__(self, frames_queue):
        self.frames_queue = frames_queue

    def start(self):
        self.show_output_callback = tornado.ioloop.PeriodicCallback(self._display, 30)
        self.show_output_callback.start()

    def stop(self):
        if self.show_output_callback and self.show_output_callback.is_running():
            self.show_output_callback.stop()
            print('destroyAllWindows')
            cv2.destroyAllWindows()

    def _display(self):
        try:
            data = self.frames_queue.get(timeout=1)
            frame = cv2.cvtColor(data, cv2.COLOR_RGB2BGR)
            cv2.imshow('Video', frame)
            cv2.waitKey(1)

        except queue.Empty:
            print('[EMPTY] output_q')
            return

