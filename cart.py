import time
from serial_handler.screen import Screen
import common.settings as settings
from common.queue import Queue
import numpy as np
import tornado.ioloop

class Cart:
    '''
        虚拟购物车
    '''
    MIN_ADD_THRESHOLD = 2
    MIN_REMOVE_THRESHOLD = 2

    def __init__(self, io):
        self.IO = io

        self.start_weight = None
        self.scale_vals = Queue(6)

        self.theoryWeight = 0
        self.realWeight = 0

        self.items = {}
        self.screen = io.screen
        self.lastActionTime = None

        if settings.has_scale:
            cartCheck = tornado.ioloop.PeriodicCallback(self.cart_check,150)
            cartCheck.start()
        

    def timeCheck(self,actionTime):
        if self.lastActionTime is None:
            self.lastActionTime = actionTime

        delta = abs(actionTime - self.lastActionTime)
        if delta > 0 and delta < 0.2:
            return True

        return False

    def add_item(self, item_id,actionTime):  # TODO: update screen display
        if self.timeCheck(actionTime):
            return

        if item_id in self.items:
            self.items[item_id] += 1
        else:
            self.items[item_id] = 1

        self.theoryWeight += settings.items[item_id]["weight"]

        self.IO.update_screen_item(True,item_id)

        self.lastActionTime = actionTime

    def remove_item(self, item_id,actionTime):
        if self.timeCheck(actionTime):
            return

        if item_id in self.items and self.items[item_id] > 0:
            self.items[item_id] -= 1

            self.theoryWeight -= settings.items[item_id]["weight"]

            self.IO.update_screen_item(False,item_id)
            self.lastActionTime = actionTime
            return True

        return False


    def getStartWeight(self):
        return self.start_weight


    def setStartWeight(self,weight):
        self.start_weight = weight


    def cart_check(self):
        weight = self.IO.get_stable_scale()

        if self.start_weight is None:
            return

        self.scale_vals.enqueue(weight)
        vals = self.scale_vals.getAll()
        _mean = int(np.mean(vals))
        for val in vals:
            if abs(_mean-val) >20:
                return

        # print("enter cart empty check:")
        # print("start_weight: ",self.start_weight," current is: ",_mean)


        delta = self.start_weight - _mean
        #empty current cart
        # if abs(self.realWeight - self.theoryWeight) < 50:
        if abs(delta) < 100:
            for _id,num in self.items.items():
                for i in range(num):
                    self.IO.update_screen_item(False,_id)
            self.items={}


    def as_order(self):
        from common.util import get_mac_address
        return dict(data=self.items,code=get_mac_address())
