import common.settings as settings
from serial_handler.door_lock import DoorLockHandler
from serial_handler.speaker import Speaker
from serial_handler.scale import WeightScale
from serial_handler.screen import Screen
import common.settings as settings
from common.queue import Queue
import tornado.ioloop
import time

class IO_Controller:#统一管理所有IO设备，增加代码清晰度
    def __init__(self):
        self.blocking = False

        #连接各个串口
        self.speaker = Speaker()
        self.scale = WeightScale()
        self.screen = Screen()
        #门和锁
        self.doorLock = DoorLockHandler()

        self.scale_vals = Queue(6)
        self.stable_scale_val = 0

        # self.val_scale = self._check_weight_scale()
        # self.envoked = False

        scaleUpdate = tornado.ioloop.PeriodicCallback(self._check_weight_scale,100)
        scaleUpdate.start()

    # def start(self):
    #     scaleUpdate = tornado.ioloop.PeriodicCallback(self._check_weight_scale,50)
    #     scaleUpdate.start()
    #     pass

    def _check_weight_scale(self):
        # import time
        # settings.logger.info("before time is:",time.time())
        self.scale_vals.enqueue(self.scale.read()*1000)

        # mean_val = .0

        # cnt=0
        # for val in self.scale_vals.getAll():
        #     mean_val += val
        #     cnt+=1

        # mean_val /= cnt

        _min,_max=10000000,0

        # isStable = True
        for val in self.scale_vals.getAll():
            if val < _min:
                _min = val
            if val > _max:
                _max = val
            # if abs(val-mean_val) > 50:
                # isStable=False
                # print("couldn't generate stable scale value ",val,mean_val)
                # break

        meanVal = .0
        cnt=0
        for val in self.scale_vals.getAll():
            if val > _min and val < _max:
                cnt+=1
                meanVal+=val
        
        # if isStable:
        if cnt != 0:
            self.stable_scale_val = meanVal/cnt
            # print("stable is: ",self.stable_scale_val)
        # else:
            # for val in self.scale_vals.getAll():
            #     print(val)
            # print("            ")
            # pass
        # settings.logger.info("after time is:",time.time())

    def get_stable_scale(self):
        return self.stable_scale_val

    '''
    	speaker部分接口
    '''
    def say_welcome(self):
        self.speaker.say_welcome()

    def say_goodbye(self):
        self.speaker.say_goodbye()
    '''
    	speaker部分接口
    '''




    '''
    	screen部分接口
    '''
    def change_to_welcome_page(self):
        self.screen.change_to_page(Screen.WELCOME_PAGE)

    def change_to_inventory_page(self):
        self.screen.change_to_page(Screen.INVENTORY_PAGE)

    def change_to_processing_page(self):
        
        self.screen.change_to_page(Screen.PROCESSING_PAGE)

    def update_screen_item(self,isAdd,itemId):
    	self.screen.update_item(isAdd,itemId)
    '''
    	screen部分接口
    '''





    '''
    	Door的接口
    '''
    def is_door_open(self, curside):

        if settings.machine_state == "new":
            return self.doorLock.is_door_open(curside)
        else:
            return self.doorLock.old_is_door_open(curside)


    def is_door_lock(self, debugTime = None, curSide = None):
        # return self.doorLock.is_door_lock()
        if settings.machine_state == "new":
            return self.doorLock.is_door_lock()
        else:
            if debugTime:
                return True if time.time() - debugTime > 7 else False
            else:
                return not self.is_door_open(curSide)


    # def both_door_closed(self, curside):
    #     return self.doorLock.both_door_closed() #peihuo

    def lock_up_door_close(self, curside):
        if settings.machine_state == "new":
            return self.doorLock.lock_up_door_close(curside)
        else:
            return True
            
    def lock_down_door_open(self, curside):
        return self.doorLock.lock_down_door_open(curside)

    def reset_lock(self, side):
        self.doorLock.reset_lock(curside)
    '''
    	Door的接口
    '''



    '''
    	Lock部分接口
    '''
    def unlock(self,side):
        self.doorLock.unlock(side)
    '''
    	Door与Lock部分接口
    '''
    

 