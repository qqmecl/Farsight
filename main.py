# -*- coding: utf-8 -*-
import argparse
from setproctitle import setproctitle
import multiprocessing
import common.settings
import os

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-num-w', '--num-workers', type=int, default=1, help='每个摄像头对应的后台进行图像识别的进程数')

    args = parser.parse_args()

    if not os.path.exists('/home/votance/Projects/Output'):
        os.makedirs('/home/votance/Projects/Output')
    
    setproctitle('[farsight] main process')

    # TODO: 使用 fork 方式似乎会导致信号捕获错乱的问题，待验证
    multiprocessing.set_start_method('spawn')#windows only spawn

    multiprocessing.log_to_stderr()

    from closet import Closet
    Closet(**vars(args)).start()
