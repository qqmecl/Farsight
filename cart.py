import time
from serial_handler.screen import Screen
import common.settings as settings
from common.queue import Queue
import numpy as np
import tornado.ioloop

class Cart:
    MIN_ADD_THRESHOLD = 2
    MIN_REMOVE_THRESHOLD = 2

    def __init__(self, io):
        self.IO = io
        self.items = {}
        self.screen = io.screen

        if settings.has_scale:
            self.scale_vals = Queue(6)
            self.start_weight = None
            self.init_weight = None

            self.before_doorOpen_weight = None
            self.after_doorClose_weight = None

            self.lastActionItem = None
            self.lastActionTime = None

            cartCheck = tornado.ioloop.PeriodicCallback(self.cart_check,60)
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

        settings.logger.warning('camera shot Take out {0}'.format(settings.items[item_id]["name"]))
        self.IO.update_screen_item(True,item_id)

        if settings.has_scale:
            self.lastActionItem = item_id
            self.lastActionTime = actionTime

    def remove_item(self, item_id,actionTime):
        if self.timeCheck(actionTime):
            return

        if item_id in self.items and self.items[item_id] > 0:
            self.items[item_id] -= 1

            settings.logger.warning('camera shot Put back {0}'.format(settings.items[item_id]["name"]))
            self.IO.update_screen_item(False,item_id)

            if settings.has_scale:
                self.lastActionItem = item_id
                self.lastActionTime = actionTime

            return True

        return False


    def getStartWeight(self):
        return self.start_weight


    def setStartWeight(self,weight):
        self.start_weight = weight
        # self.theoryWeight = weight
        print("start weight is: ",weight)

        if self.init_weight is None:
            self.init_weight = weight

    def setBeforDoorOpenWeight(self):
        self.before_doorOpen_weight = self.IO.get_stable_scale()

    def setAfterDoorCloseWeight(self):
        self.after_doorClose_weight = self.IO.get_stable_scale()
       
    def cart_check(self):
        if self.start_weight is None:
            return


        weight = self.IO.get_stable_scale()

        self.scale_vals.enqueue(weight)
        vals = self.scale_vals.getAll()
        _mean = int(np.mean(vals))
        for val in vals:
            if abs(_mean-val) >20:
                return

        # print("enter cart empty check:")
        # print("start_weight: ",self.start_weight," current is: ",_mean)


        delta = self.init_weight - _mean

        # self.realWeight = _mean

        #empty current cart
        # if abs(self.realWeight - self.theoryWeight) < 50:
        if abs(delta) < 70:
            for _id,num in self.items.items():
                for i in range(num):
                    self.IO.update_screen_item(False,_id)
            self.items={}
            self.lastPutBack=None
            self.lastTakeOut=None
            return


        theoryWeight = self.start_weight

        for _id,num in self.items.items():
            for i in range(num):
                theoryWeight -= settings.items[_id]["weight"]


        delta2 = theoryWeight - _mean

        # print("start_weight is: ",self.start_weight)
        # print("theoryWeight is: ",theoryWeight)
        # print("realWeight is: ",_mean)
        # print("delta2 is: ",delta2)

        if delta2 > 100:
            if self.lastActionItem != None:
                self.add_item(self.lastActionItem,self.lastActionTime)
                self.lastActionItem = None
        elif delta2 < -100:
            if self.lastActionItem != None:
                self.remove_item(self.lastActionItem,self.lastActionTime)
                self.lastActionItem = None


    def as_order(self):
        from common.util import get_mac_address

        return dict(data=self.items,code=get_mac_address())

    def isEmpty(self):
        return len(self.items)==0

    def reset(self):
        self.items={}
