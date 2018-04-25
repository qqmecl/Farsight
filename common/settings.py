import os
import multiprocessing
from common.util import get_mac_address
from common.logger import Logger

INIT_URL = "https://www.hihigo.shop/api/v1/updateGoodsInfo"
ORDER_URL = 'https://www.hihigo.shop/api/v1/order'

<<<<<<< HEAD
=======
items = {
    '6921168509256001': dict(name='农夫山泉矿泉水', price=2.0, weight=575.0),
    '6956416200067001': dict(name='美汁源果粒橙', price=5.0, weight=487.0),
    '6920202888883001': dict(name='红牛', price=8.0, weight=298.0),
    '6902538006100001': dict(name='脉动', price=6.5, weight=650.0),
    '6921581596048001': dict(name='三得利乌龙茶', price=6.0, weight=528.0),
    '6920459989463001': dict(name='冰糖雪梨', price=6.0, weight=549.0),
    '4891028705949001': dict(name='维他柠檬茶', price=7.0, weight=552.0),
    '6901939621271001': dict(name='雪碧听装', price=3.5, weight=343.0),
    '6901939621608001': dict(name='可口可乐听装', price=3.5, weight=354.0),
    '6925303730574001': dict(name='统一阿萨姆奶茶', price=6.5, weight=550.0),
    '6925303754952001': dict(name='小茗同学黄色', price=6.5, weight=546.0),
    '6925303714857001': dict(name='汤达人豚骨面', price=13.5, weight=184.0),
    '0000000000000001': dict(name='empty_hand', price=13.5, weight=184.0),
}

>>>>>>> f2198f453693d686c83ca287b319bf8f3c72ea22
# items = {
#     '6921168509256001': dict(name='农夫山泉矿泉水', price=2.0, weight=575.0),
#     '6956416200067001': dict(name='美汁源果粒橙', price=5.0, weight=487.0),
#     '6920202888883001': dict(name='红牛', price=8.0, weight=298.0),
#     '6902538006100001': dict(name='脉动', price=6.5, weight=650.0),
#     '6921581596048001': dict(name='三得利乌龙茶', price=6.0, weight=528.0),
#     '6920459989463001': dict(name='冰糖雪梨', price=6.0, weight=549.0),
#     '4891028705949001': dict(name='维他柠檬茶', price=7.0, weight=552.0),
#     '6901939621271001': dict(name='雪碧听装', price=3.5, weight=343.0),
#     '6901939621608001': dict(name='可口可乐听装', price=3.5, weight=354.0),
#     '6925303730574001': dict(name='统一阿萨姆奶茶', price=6.5, weight=550.0),
#     '6925303754952001': dict(name='小茗同学黄色', price=6.5, weight=546.0),
#     '6925303714857001': dict(name='汤达人豚骨面', price=13.5, weight=184.0),
# }

<<<<<<< HEAD
items = {
    '6901347884138': dict(name='椰树牌椰汁', price=2.0, weight=575.0),
    '6924743920538': dict(name='多力多滋玉米片', price=5.0, weight=487.0),
    '6925303714086': dict(name='统一红烧牛肉面', price=8.0, weight=298.0),
    '6925303773106': dict(name='统一老坛酸菜牛肉面', price=6.5, weight=546.0),
    '6925668475288': dict(name='顶牛素牛筋', price=6.0, weight=528.0),
    '6941760904372': dict(name='美好小火锅特辣', price=6.0, weight=549.0),
    '6952032902088': dict(name='蛙稻米大米', price=7.0, weight=552.0),
    '0000000000001': dict(name='empty_hand', price=3.5, weight=343.0)
}

http_port = 5000
=======
>>>>>>> f2198f453693d686c83ca287b319bf8f3c72ea22
sea_key = None

welcome_page = {'D8:9E:F3:1D:E6:9E': 0x33,'D8:9E:F3:1D:EE:7C': 0x0D,'D8:9E:F3:1E:13:8A': 0x33}
WELCOME_PAGE = welcome_page.get(get_mac_address(), 0x33)

#Load basic config corresponding to every different machine.

from configparser import ConfigParser
config_parser = ConfigParser()
config_parser.read("/home/votance/Projects/Farsight/local/config.ini")

camera_width  = config_parser.getint("usb_cameras","width")
camera_height = config_parser.getint("usb_cameras","height")
camera_number = config_parser.getint("usb_cameras","number")

usb_cameras=[]
detect_baseLine=[]

<<<<<<< HEAD
box_style = config_parser.get("box_style", "style")
android_screen = config_parser.getboolean("box_style", "android")

for i in range(2):
=======
for i in range(camera_number):
>>>>>>> f2198f453693d686c83ca287b319bf8f3c72ea22
    content = config_parser.get("usb_cameras","index"+str(i))
    usb_cameras.append(content)
    centerX = config_parser.getint("base_line","centerX"+str(i))
    detect_baseLine.append(centerX)

<<<<<<< HEAD
SAVE_VIDEO_OUTPUT = config_parser.getboolean("maintain_switch","save_video_output")
=======
>>>>>>> f2198f453693d686c83ca287b319bf8f3c72ea22

#hardware configuration
camera_version = config_parser.getint("hardware","camera_version")
lock_version = config_parser.getint("hardware","lock_version")

speaker_on = config_parser.getboolean("maintain_switch","speaker_on")

#serial ports configuration
door_port = config_parser.get("serial_ports","door_port")
if box_style == 'double':
    speaker_port = config_parser.get("serial_ports","speaker_port")
    scale_port = config_parser.get("serial_ports","scale_port")
screen_port = config_parser.get("serial_ports","screen_port")


has_scale = config_parser.getboolean("run_mode","withscale")
<<<<<<< HEAD
=======
is_offline = config_parser.getboolean("run_mode","offline")

>>>>>>> f2198f453693d686c83ca287b319bf8f3c72ea22
logger = Logger(config_parser.get("run_mode","client_mode"))