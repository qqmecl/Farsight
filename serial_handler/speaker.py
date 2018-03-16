import serial
import struct
from serial_handler.crc import crc16
import functools
import tornado.ioloop
import settings
import time

class Speaker:#简单触发器
    '''
        控制扬声器发声
    '''
    def __init__(self,port="/dev/ttyS0"):
        rate = 9600
        self.com = serial.Serial(port, baudrate=rate, timeout=1)

    def do_protocol_5_byMode(self,addr,isOpen):#设置有宽度脉冲进行触发
        array = [1, 5, 0, addr, 0xff if isOpen else 0x00, 0]
        cmd = crc16().createarray(array)
        data = struct.pack(str(len(cmd)) + "B", *cmd)
        self.com.write(data)
        self.com.read(8)#读掉数据，如果不读掉数据，会影响后续的数据读取

    def say_welcome(self):
        self.do_protocol_5_byMode(2,True)#2表示端口地址，1秒之后重置该口状态
        reset = functools.partial(self.reset_welcome)
        tornado.ioloop.IOLoop.current().call_later(self, delay=1, callback=reset)
        # array = list(map(ord, ':161fffff'))
        # array = [1, 5, 0, 2, 0xff, 0]
        # settings.logger.info(array)
        # data = struct.pack(str(len(array)) + "B", *array)
        # # cmd = crc16().createarray(array)
        # # data = struct.pack(str(len(cmd)) + "B", *cmd)
        # settings.logger.info(data)
        # self.com.write(data)
        # settings.logger.info(self.com.read(8))#读掉数据，如果不读掉数据，会影响后续的数据读取

    def reset_welcome(self):
        self.do_protocol_5_byMode(2,False)#2表示端口地址，1秒之后重置该口状态

    def say_goodbye(self):
        self.do_protocol_5_byMode(3,True)
        reset = functools.partial(self.rest_goodbye)
        tornado.ioloop.IOLoop.current().call_later(self, delay=1, callback=reset)
        # array = list(map(ord, ':162fffff'))
        # data = struct.pack(str(len(array)) + "B", *array)

        # self.com.write(data)
        # self.com.read(8)  # 读掉数据，如果不读掉数据，会影响后续的数据读取

    def rest_goodbye(self):
        self.do_protocol_5_byMode(3,False)#2表示端口地址，1秒之后重置该口状态


if __name__ == '__main__':
    speaker = Speaker()
    speaker.say_welcome()
    # speaker.do_goodbye()

    tornado.ioloop.IOLoop.current().start()##this should be like server .start will forever monitor io input.
    # speaker.rest_welcome()
    # speaker.rest_goodbye()
    # say_goodbye()
