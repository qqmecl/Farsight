import random
import multiprocessing
import os
import threading

logger = multiprocessing.get_logger()


def selfcheck():
    logger.info('=================== MOCK: [SELFCHECK] pass {} ==================='.format(os.getpid()))


class WeightScale:
    def __init__(self, port='COM1'):
        pass

    def read(self):
        return random.random()


class Speaker:
    def __init__(self, port='COM1'):
        pass

    def say_welcome(self):
        logger.info('=================== MOCK: [SPEAKER] welcome ===================')

    def say_goodbye(self):
        logger.info('=================== MOCK: [SPEAKER] goodbye ===================')


class Screen:
    INVENTORY_PAGE = 'INVENTORY_PAGE'
    PROCESSING_PAGE = 'PROCESSING_PAGE'

    def __init__(self, port='COM1'):
        logger.info('=================== MOCK: [Screen] init ===================')

    def change_to_page(self, page):
        print('changing to page: ', page)

    def update_item(self, isAdd, itemId):
        if isAdd:
            print("AddItemId is: ",itemId)
        else:
            print("RemoveItemId is: ",itemId)


class DoorLockHandler:
    LEFT_DOOR = 0
    RIGHT_DOOR = 1

    def __init__(self, port='COM1'):
        self.logger = multiprocessing.get_logger()
        # TODO: 发送网络请求自动模拟本地网络调用.5秒钟后自动开门
        # threading.Timer(5, self.autoUnlock).start()
        self.door_open = False

    def autoUnlock(self):
        import urllib.request
        urllib.request.urlopen("http://localhost:8888/door?secret=grtrgewfgvs&token=haha").read()

    def unlock(self, side):
        # self.door_open = True
        threading.Timer(10, self.close_door).start()
        self.logger.info('=================== MOCK: [LOCK] unlock side: {0} ==================='.format(side))

    def both_lock_locked(self):
        return True

    def both_door_closed(self):
        return True

    def is_door_open(self, side):
        return self.door_open

    def close_door(self):
        self.door_open = False


if __name__ == '__main__':
    # DoorHandler().unlock('left')
    Speaker().say_welcome()
