import sys
# import cv2
import multiprocessing

class SignalHandler:
    def __init__(self, camera_process, object_detection_pools, ioloop):
        self.camera_process = camera_process
        self.object_detection_pools = object_detection_pools
        self.ioloop = ioloop
        self.logger = multiprocessing.get_logger()

    def signal_handler(self, signal, frame):
        self.logger.info('正在退出...')
        self.camera_process.terminate()

        for pool in self.object_detection_pools:
            pool.terminate()

        self.ioloop.stop()
        # cv2.destroyAllWindows()
        sys.exit(0)
