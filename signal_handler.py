import sys
import multiprocessing
import common.settings as settings

class SignalHandler:
    def __init__(self, object_detection_pools, ioloop):
        self.object_detection_pools = object_detection_pools
        self.ioloop = ioloop
        self.logger = multiprocessing.get_logger()

    def signal_handler(self, signal, frame):
        settings.logger.info('shutdown...')

        for pool in self.object_detection_pools:
            pool.terminate()

        self.ioloop.stop()
        # cv2.destroyAllWindows()
        sys.exit(0)
