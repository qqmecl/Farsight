# -*- coding: utf-8 -*-
import argparse
from setproctitle import setproctitle
import multiprocessing
import common.settings
import os

if __name__ == '__main__':
    parser = argparse.ArgumentParser()#argparse 命令项选项与参数解析的模块 例如在命令行中决定摄像头运行数量
    parser.add_argument('-num-w', '--num-workers', type=int, default=1, help='每个摄像头对应的后台进行图像识别的进程数')

    args = parser.parse_args()

    if not os.path.exists('/home/votance/Projects/Output'):
        os.makedirs('/home/votance/Projects/Output')#创建用来存储视频和log的地址
    
    setproctitle('[farsight] main process')#设置进程名称

    # TODO: 使用 fork 方式似乎会导致信号捕获错乱的问题，待验证
    multiprocessing.set_start_method('spawn')#windows only spawn

    multiprocessing.log_to_stderr()

    from closet import Closet
    Closet(**vars(args)).start()#closet类是代表整个柜体
