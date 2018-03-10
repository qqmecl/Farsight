# -*- coding: utf-8 -*-

import argparse
from setproctitle import setproctitle
import multiprocessing
import settings
import logging

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help='Enable debug info')
    parser.add_argument('-num-w', '--num-workers', type=int, default=1, help='每个摄像头对应的后台进行图像识别的进程数')

    parser.add_argument('--visualize-camera', type=int, help='输出捕获视频的摄像头编号（debug用）')

    parser.add_argument('--left-cameras', nargs='+', type=int, help='设置左边摄像头编号列表，-1 为空')
    #parser.set_defaults(left_cameras=[0])#Maybe adjustable
    parser.set_defaults(left_cameras=[0,1])#Maybe adjustable

    parser.add_argument('--right-cameras', nargs='+', type=int, help='设置右边摄像头编号列表，-1 为空')
    parser.set_defaults(right_cameras=[2, 3])
    #parser.set_defaults(right_cameras=[2])

    parser.add_argument('--mock-door', action='store_true', help='是否 MOCK 门和锁')
    parser.set_defaults(mock_door=False)
    parser.add_argument('--mock-speaker', action='store_true', help='是否 MOCK 扬声器')
    parser.set_defaults(mock_speaker=False)
    parser.add_argument('--mock-scale', action='store_true', help='是否 MOCK 重量计')
    parser.set_defaults(mock_scale=False)
    parser.add_argument('--mock-screen', action='store_true', help='是否 MOCK 显示屏')
    parser.set_defaults(mock_screen=False)

    parser.add_argument('--run-mode', type=str, help='set running mode')
    parser.set_defaults(run_mode="CPU")

    parser.add_argument('--sell-mode', type=str, help='set running mode')
    parser.set_defaults(run_mode="develop")


    parser.add_argument('--speaker-port', type=str, help='扬声器 COM 口')
    parser.set_defaults(speaker_port="/dev/ttyS0")

    parser.add_argument('--door-port', type=str, help='门和锁的 COM 口')
    parser.set_defaults(door_port="/dev/ttyS0")

    parser.add_argument('--scale-port', type=str, help='重量计 COM 口')
    parser.set_defaults(scale_port="/dev/ttyS4")

    parser.add_argument('--screen-port', type=str, help='显示屏 COM 口')
    parser.set_defaults(screen_port="/dev/ttyS5")

    parser.add_argument('--http-port', type=str, help='HTTP 监听端口')
    parser.set_defaults(http_port='5000')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(name)s:%(levelname)s: %(message)s")
    #logger = logging.getLogger()

    if args.verbose:
        settings.logger.setLevel(logging.INFO)
    else:
        settings.logger.setLevel(logging.WARN)
    
    setproctitle('[farsight] main process')

    # TODO: 使用 fork 方式似乎会导致信号捕获错乱的问题，待验证
    multiprocessing.set_start_method('spawn')#windows only spawn
    multiprocessing.log_to_stderr()

    settings.mock_door = args.mock_door
    settings.mock_speaker = args.mock_speaker
    settings.mock_scale = args.mock_scale
    settings.mock_screen = args.mock_screen

    settings.scale_port = args.scale_port


    from closet import Closet

    Closet(**vars(args)).start()
