import sys
# import cv2
import multiprocessing
import settings

class SignalHandler:
    def __init__(self, camera_process, object_detection_pools, ioloop, chen_loop):
        self.camera_process = camera_process
        self.object_detection_pools = object_detection_pools
        self.ioloop = ioloop
        self.chen_loop = chen_loop
        self.logger = multiprocessing.get_logger()

    def signal_handler(self, signal, frame):
        settings.logger.info('shutdown...')
        self.camera_process.terminate()

        for pool in self.object_detection_pools:
            pool.terminate()
        self.chen_loop.close()

        self.ioloop.stop()
        # cv2.destroyAllWindows()
        sys.exit(0)
