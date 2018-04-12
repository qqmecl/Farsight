# -*- coding: utf-8 -*-
import argparse
from setproctitle import setproctitle
import multiprocessing
import common.settings
import os

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', dest='dev', help='Enable debug info')
    parser.add_argument('-num-w', '--num-workers', type=int, default=1, help='每个摄像头对应的后台进行图像识别的进程数')

    parser.add_argument('--left-cameras', nargs='+', type=int, help='设置左边摄像头编号列表，-1 为空')
    parser.set_defaults(left_cameras=[0,1])

    parser.add_argument('--right-cameras', nargs='+', type=int, help='设置右边摄像头编号列表，-1 为空')
    parser.set_defaults(right_cameras=[2, 3])


    parser.add_argument('--speaker-port', type=str, help='扬声器 COM 口')
    parser.set_defaults(speaker_port="/dev/ttyS0")

    parser.add_argument('--door-port', type=str, help='门和锁的 COM 口')
    parser.set_defaults(door_port="/dev/ttyS0")

    parser.add_argument('--scale-port', type=str, help='重量计 COM 口')
    parser.set_defaults(scale_port="/dev/ttyS4")

    parser.add_argument('--screen-port', type=str, help='显示屏 COM 口')
    parser.set_defaults(screen_port="/dev/ttyS1")

    args = parser.parse_args()

    if not os.path.exists('/home/votance/Projects/Output'):
        os.makedirs('/home/votance/Projects/Output')
    
    setproctitle('[farsight] main process')

    # TODO: 使用 fork 方式似乎会导致信号捕获错乱的问题，待验证
    multiprocessing.set_start_method('spawn')#windows only spawn
    multiprocessing.log_to_stderr()

    from closet import Closet

    Closet(**vars(args)).start()
