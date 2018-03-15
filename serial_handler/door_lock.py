import serial
import struct
from serial_handler.crc import crc16
import threading
import time
import functools
import tornado.ioloop
import settings

# 开某一边门之前要判断另一边锁是否打开，若打开，则不能开锁
# 此处分门和智能锁，工控机接收到信号之后先开锁
# 并且锁被开启之后，在不开门状态下过3秒之后会自动上锁
# 处于开门状态不会上锁
class DoorLockHandler:
    LEFT_DOOR = settings.LEFT_DOOR
    RIGHT_DOOR = settings.RIGHT_DOOR

    #串口地址可配置
    def __init__(self, port="/dev/ttyS0"):
        rate = 9600
        self.com = serial.Serial(port, baudrate=rate, timeout=1)
        # self.lock = threading.Lock()

    def _read_status(self):
        data = self.com.read(6)[3]
        # settings.logger.info(data)
        return data

    def _send_data(self, array):
        cmd = crc16().createarray(array)
        data = struct.pack(str(len(cmd)) + "B", *cmd)
        self.com.write(data)


    #只检测磁感应继电器状态判断左门，右门是否关闭
    def is_door_open(self, side):
        '''
            检测门是否打开
        '''
        # with synchronized(self.lock):
        self._send_door_statuscheck()
        data = self._read_status()

        other_side = 1 - side  # 1 -> 0, 0 -> 1
        if data & (other_side + 1) == 0:
            # 另外一边门开了
            # 后台报警
            # raise DoorError('另外一边门怎么开了？？')TODO
            pass

        return data & (side + 1) == 0

    def both_door_closed(self):
        '''
            用于自检和配货：确保两个门都是关闭的
        '''
        #门关上之后为高电平，锁与门真正结合之后才为锁上门
        # with synchronized(self.lock):
        self._send_door_statuscheck()
        data = self._read_status()

        return data & 3 == 3

    def _send_door_statuscheck(self):
        array = [1, 2, 0, 0, 0, 4]
        self._send_data(array)





    #解开锁的状态，以开启门，并过2s之后重置电平信号
    def unlock(self, side):
        '''
            打开一边的锁，会自动延时重置锁的状态
        '''
        # TODO:确保状态是关闭
        array = [1, 5, 0, side, 0xff, 0]  # TODO
        self._send_data(array)
        self.com.read(8)  #读掉数据，如果不读掉数据，会影响后续的数据读取
        reset = functools.partial(self.reset_lock,side)
        tornado.ioloop.IOLoop.current().call_later(delay=1,callback=reset)

    #重置电平信号
    def reset_lock(self, side):
        '''
            重置一边的锁，一般情况下不需要主动调用
            TODO: 在自检时如果发现锁需要重置，则进行重置（如程序异常退出等）
        '''
        array = [1, 5, 0, side, 0, 0]
        self._send_data(array)
        self.com.read(8)


    #检测某一边锁是否是高电平信号
    def is_lock_status_on(self, side):
        '''
            检测是否高电平，如果是的话，需要先 reset_lock
        '''
        # with synchronized(self.lock):
        self._send_lock_statuscheck()
        data = self._read_status()

        return bool(data & (side + 1))

    def both_lock_locked(self):
        '''
            用于自检：确保两个锁都是关闭的
        '''
        # with synchronized(self.lock):
        self._send_lock_statuscheck()
        data = self._read_status()

        return data & 3 == 0

    def _send_lock_statuscheck(self):
        array = [1, 1, 0, 0, 0, 4]
        self._send_data(array)


if __name__ == '__main__':
    handler = DoorLockHandler()

    #分为锁和门
    # handler.unlock(DoorLockHandler.LEFT_DOOR)  # 开左边锁，以打开门

    # handler.reset_lock(DoorLockHandler.LEFT_DOOR)
    # handler.reset_lock(DoorLockHandler.RIGHT_DOOR)


    # settings.logger.info(handler.is_door_open(DoorLockHandler.LEFT_DOOR))

    settings.logger.info(handler.both_door_closed())
    # settings.logger.info(handler.both_door_closed())
    # settings.logger.info(handler.both_lock_locked())
