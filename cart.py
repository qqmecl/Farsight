import time
from serial_handler.screen import Screen
import common.settings as settings

class Cart:
    '''
        虚拟购物车
    '''
    MIN_ADD_THRESHOLD = 2
    MIN_REMOVE_THRESHOLD = 2

    def __init__(self, io):
        self.IO = io
        self.start_weight = self.IO.get_stable_scale()
        self.items = {}
        self.screen = io.screen
        self.lastActionTime = None

    def timeCheck(self,actionTime):
        if self.lastActionTime is None:
            self.lastActionTime = actionTime

        delta = abs(actionTime - self.lastActionTime)

        print("cart delta ",delta)

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

        self.IO.update_screen_item(True,item_id)

        self.lastActionTime = actionTime

    def remove_item(self, item_id,actionTime):
        if self.timeCheck(actionTime):
            return

        if item_id in self.items and self.items[item_id] > 0:
            self.items[item_id] -= 1
            self.IO.update_screen_item(False,item_id)

            self.lastActionTime = actionTime

            return True
        else:
            pass

        return False

    def clear_cart(self):
        pass

    def as_order(self):
        from common.util import get_mac_address
        return dict(data=self.items,code=get_mac_address())
