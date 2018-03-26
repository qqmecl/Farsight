import time
from serial_handler.screen import Screen
import common.settings

class Cart:
    '''
        虚拟购物车
    '''
    MIN_ADD_THRESHOLD = 2
    MIN_REMOVE_THRESHOLD = 2

    def __init__(self, user_token, io):
        self.token = user_token

        self.IO = io

        self.start_weight = self.IO.get_scale_val()
        self.items = {}
        self.screen = io.screen
        self.last_add_timestamp = time.time()
        self.last_remove_timestamp = time.time()

    def add_item(self, item_id):  # TODO: update screen display
        '''
            添加商品到购物车，如果添加过快，会被忽略
        '''

        # self.items[item_id] += 1

        if item_id in self.items:
            self.items[item_id] += 1
        else:
            self.items[item_id] = 1

        settings.logger.info("Cart add action!!!!!!!!!!!!!")
        # if self.items[item_id] > 0:
        self.IO.update_screen_item(True,item_id)

    def remove_item(self, item_id):
        '''
            购物车移除商品，如果操作过快，会被忽略
        '''
        if item_id in self.items and self.items[item_id] > 0:
            self.items[item_id] -= 1

            settings.logger.info("Trully remove item!!")

            self.IO.update_screen_item(False,item_id)

            return True
        else:
            pass
            # TODO:
            # settings.logger.info('Try to clear an item which is not included in the closet!')
        self.last_remove_timestamp = time.time()
        
        return False
    # def isHaveItem(self,item_id):
        # return self.items[item_id] > 0


    def as_order(self):
        '''
            转换成下单所需的格式
            TODO: 机器对应的 code 应该从配置中读取
        '''
        import utils
        
        return dict(
            data=self.items,
            token=self.token,
            code=settings.get_mac_address(),
            weight=dict(start=self.start_weight, final=self.IO.get_scale_val())
        )


if __name__ == '__main__':
    cart = Cart('fye', 10)
    cart.add_item('123123')
    cart.add_item('123123')
    cart.add_item('123123')
    cart.add_item('122003')
    cart.remove_item('123123')
    cart.remove_item('12311312323')
    settings.logger.info('{data} {token} {code} {weight}'.format(**cart.as_order()))
