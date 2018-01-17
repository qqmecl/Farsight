#!/usr/bin/env python
# -*- coding: utf-8 -*-
from serial_handler.crc import crc16
import serial
import struct
import itertools
import functools
import tornado.ioloop
import settings


class Screen:
    CHANGE_PAGE_ADDRESS = 0

    CART_COUNT_ADDRESS = 200
    CART_TOTAL_ADDRESS = 201

    WELCOME_PAGE = settings.WELCOME_PAGE
    
    INVENTORY_PAGE = 0x34

    PROCESSING_PAGE = 0x36
    ALL_COUNT_ADDRESS = 200
    ALL_TOTAL_ADDRESS = 201

    PROTOCOL_6_LEN = 8  # 06功能码长度
    ITEM_NAME_START_ADDRESS = 500  # 单行商品起始地址
    ITEM_NAME_INTERVAL = 50  # 单行商品间高度间隔

    ITEM_PRICE_START_ADDRESS = 100  # 单行商品价格起始地址
    ITEM_PRICE_INTERVAL = 10  # 单行商品价格间高度间隔

    ITEM_NUM_START_ADDRESS = 101  # 单行商品数量起始地址
    ITEM_NUM_INTERVAL = 10  # 单行商品数量间高度间隔

    LINE_MAX_LIMIT = 14  # 最大可允许行数

    def __init__(self, port="/dev/ttyS5"):
        # rate = 115200  # 当前串口通信设备波特率
        rate = 9600  # 当前串口通信设备波特率
        self.com = serial.Serial(port, baudrate=rate, timeout=1)
        self.resetData()

    def resetData(self):
        self.curItems = []  # [['007001','维他柠檬茶',700,1]]id,name,price,num
        self.cartCount = 0
        self.cartPrice = 0

    # 开放给外部的物品更新接口1，增减item
    def update_item(self, isAdd, itemId):  # 当前速度较慢，后期需提高用户体验
        # 对商品id增减逻辑进行判断
        fromDeleteIndex = -1
        isNewItem = True
        # print(self.curItems)
        for i, item in enumerate(self.curItems):
            if itemId == item[0]:
                isNewItem = False
                name_add = 150 if i > 6 else 0
                if isAdd:
                    self.cartCount += 1
                    self.cartPrice += item[2]
                    item[3] += 1
                    self.update_Single_line(i)
                    # self.do_protocol_6(Screen.ITEM_NUM_START_ADDRESS + i * Screen.ITEM_NUM_INTERVAL + num_add, item[3])  # 写商品数量
                else:
                    self.cartCount -= 1
                    self.cartPrice -= item[2]
                    if item[3] == 1:  # 当前商品数量变为零，删除当前行，后续所有行均需前移一行
                        fromDeleteIndex = i
                        break
                    else:
                        item[3] -= 1
                        self.update_Single_line(i)
                        # self.do_protocol_6(Screen.ITEM_NUM_START_ADDRESS + i * Screen.ITEM_NUM_INTERVAL + num_add, item[3])  # 写商品数量
                break

        # print(isNewItem,self.curItems)
        
        # 如果是一种新的商品走如下逻辑
        if isNewItem:
            for _id, _dict in settings.items.items():
                if itemId == _id:
                    newItem = [_id, _dict["name"], int(_dict["price"] * 10), 1]
                    self.curItems.append(newItem)
                    self.update_Single_line(len(self.curItems) - 1)
                    self.cartCount += 1
                    self.cartPrice += newItem[2]
                    break

        if fromDeleteIndex > -1:
            # print("fromDeleteIndex is: ",fromDeleteIndex)
            lastIndex = len(self.curItems) - 1
            self.clear_line_content(lastIndex)  # 先清空最后一行内容
            del self.curItems[fromDeleteIndex]  # 从self.curItems中删除当前为零商品行
            index = lastIndex - 1
            # print(self.curItems)
            while(index >= fromDeleteIndex):
                self.update_Single_line(index)
                index -= 1

        # 最后更新总体数据统计
        self.update_static_info()

    # 开放给外部的物品更新接口2，设置页面切换
    def change_to_page(self, page):
        if page == Screen.PROCESSING_PAGE:
            for i in range(len(self.curItems)):
                self.clear_line_content(i)

            self.do_protocol_6(Screen.ALL_COUNT_ADDRESS, self.cartCount)
            # 设置process order info
            self.do_protocol_6(Screen.ALL_TOTAL_ADDRESS, self.cartPrice)

            self.resetData()
            reset = functools.partial(self.change_to_page, Screen.WELCOME_PAGE)
            tornado.ioloop.IOLoop.current().call_later(delay=4, callback=reset)
        elif page == Screen.WELCOME_PAGE:
            self.do_protocol_6(Screen.ALL_COUNT_ADDRESS,0)
            # 设置process order info
            self.do_protocol_6(Screen.ALL_TOTAL_ADDRESS,0)
        elif page == Screen.INVENTORY_PAGE:
            for i in range(7):
                self.clear_line_content(i)



        self.do_protocol_6(Screen.CHANGE_PAGE_ADDRESS, page)  # 0地址码

    # 按ModBus功能码为6的协议写数据
    def do_protocol_6(self, address, content):
        # print("address is ",address)
        conf = [0x01, 0x06, *divmod(address, 256), *divmod(content, 256)]
        array = crc16().createarray(conf)
        data = struct.pack(str(Screen.PROTOCOL_6_LEN) + "B", *array)
        self.com.write(data)
        self.com.read(Screen.PROTOCOL_6_LEN)


    # 按ModBus功能码为5的协议写数据
    def do_protocol_5(self, address, content):
        # print("5address is ",address)
        conf = [0x01, 0x05, *divmod(address, 256), 0xff,content]
        array = crc16().createarray(conf)
        data = struct.pack(str(Screen.PROTOCOL_6_LEN) + "B", *array)
        self.com.write(data)
        self.com.read(Screen.PROTOCOL_6_LEN)

    # 按ModBus功能码为16的协议写数据
    def do_protocol_16(self, address, content):
        # print("address is ",address)
        results = [0x01, 0x10, *divmod(address, 256), 0x00, len(content), len(content) * 2]
        codepoints = [divmod(ord(x), 256) for x in content]
        conf = results + list(itertools.chain.from_iterable(codepoints))
        array = crc16().createarray(conf)
        data = struct.pack(str(len(array)) + "B", *array)
        self.com.write(data)
        self.com.read(len(conf) + 2)  # 读出缓存数据

    def processItemName(self, item):
        FULL_SPACE = '　'
        HALF_SPACE = ' '

        result=item[1]
        supplement = 7 - len(item[1])
        result += ''.join([FULL_SPACE for s in range(supplement)]) + FULL_SPACE
        result += str(item[2]/10)+HALF_SPACE+"元"
        result += FULL_SPACE+FULL_SPACE+FULL_SPACE
        result += str(item[3])
        # print(result)
        return result

    def update_Single_line(self, index):
        # 先清除本行内容
        assert index < Screen.LINE_MAX_LIMIT and index > -1, "Index out of range!!!"
        self.clear_line_content(index)
        # 然后更新本行内容
        item = self.curItems[index]
        display_item = self.processItemName(item)
        add = 150 if index > 6 else 0
        # print(item,index)
        self.do_protocol_16(Screen.ITEM_NAME_START_ADDRESS + index * Screen.ITEM_NAME_INTERVAL + add,display_item)#写商品info
        # print("weird!!")  


    def update_static_info(self):
        # print("")
        # 设置购物车商品数量
        self.do_protocol_6(Screen.CART_COUNT_ADDRESS, self.cartCount)
        # 设置购物车内商品总价
        self.do_protocol_6(Screen.CART_TOTAL_ADDRESS, self.cartPrice)

    def clear_line_content(self, index):
        assert index < Screen.LINE_MAX_LIMIT and index > -1, "Index out of range!!!"
        add = 150 if index > 6 else 0
        self.do_protocol_5(Screen.ITEM_NAME_START_ADDRESS + index * Screen.ITEM_NAME_INTERVAL + add, 0)  # 写商品名称
       

    def on_close_door():
        self.change_to_page(Screen.PROCESSING_PAGE)
        for i in range(len(self.curItems)):
            self.clear_line_content(i)

        self.do_protocol_6(Screen.CART_COUNT_ADDRESS, 0)
        # 设置购物车内商品总价
        self.do_protocol_6(Screen.CART_TOTAL_ADDRESS, 0)
        # self.resetData()


if __name__ == '__main__':
    screen = Screen()

    # screen.change_to_page(Screen.INVENTORY_PAGE)

    # screen.do_protocol_6(Screen.CART_COUNT_ADDRESS,0)
    # screen.do_protocol_6(Screen.CART_TOTAL_ADDRESS,0)

    

    

    for i in range(7):
        screen.clear_line_content(i)

    screen.update_static_info()

    screen.change_to_page(Screen.WELCOME_PAGE)
    # screen.change_to_page()

    # screen.update_item(True,"007001")
    # screen.update_item(True,"001001")
    # screen.update_item(True,"001001")
    # screen.update_item(True,"006001")

    # screen.do_protocol_16(550, "fae rtewrw3er 3wrr34wrt ")  # 写商品名称

    # screen.update_item(True,"007001")

    # screen.update_item(True,"维他柠檬茶")
    # # screen.update_item(False,"维他柠檬茶")
    # screen.update_item(True,"美汁源果粒橙")
    # screen.update_item(False,"维他柠檬茶")

    # screen.update_item(True,"阿萨姆原味奶茶")
    # screen.update_item(True,"酸酸辣辣豚骨面")

    # screen.update_item(False,"美汁源果粒橙")
    # screen.update_item(True,"酸酸辣辣豚骨面")
    # screen.update_item(False,"维他柠檬茶")
