import serial
import struct
from error import FarSightError


class WeightScaleError(FarSightError):
    pass


class WeightScale:
    '''
        从重量计中读取数据
    '''
    def __init__(self, port='/dev/ttyS4'):
        rate = 9600

        self.com = serial.Serial(port, baudrate=rate, timeout=1)

    def read(self):
        # 01 04 0000 0002 71cb
        array = [1, 4, 0, 0, 0, 2, 0x71, 0xcb]

        data = struct.pack(str(len(array)) + "B", *array)

        self.com.write(data)

        raw = self.com.read(9)[slice(3, 7)]

        # 按照 IEEE 754 Float 格式 unpack
        return struct.unpack('>f', raw)



if __name__ == '__main__':
    scale = WeightScale()

    print(scale.read()[0])

