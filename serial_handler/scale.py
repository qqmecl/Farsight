import serial
import struct
import common.settings as settings

class WeightScale:
    '''
        从重量计中读取数据
    '''
    def __init__(self, port=settings.scale_port):
        rate = 9600
        
        if settings.scale_port != "none":
            self.com = serial.Serial(port, baudrate=rate, timeout=1)

    def read(self):
        # 01 04 0000 0002 71cb
        if settings.scale_port != "none":
            array = [1, 4, 0, 0, 0, 2, 0x71, 0xcb]

            data = struct.pack(str(len(array)) + "B", *array)
            self.com.write(data)
            raw = self.com.read(9)[slice(3, 7)]
            # 按照 IEEE 754 Float 格式 unpack
            return struct.unpack('>f', raw)[0]
        else:
            return 1.0

if __name__ == '__main__':
    scale = WeightScale(port="/dev/ttyS4")
    print(scale.read()[0])

