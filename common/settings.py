import os
import multiprocessing
from common.util import get_mac_address
from common.logger import Logger

INIT_URL = "https://www.hihigo.shop/api/v1/updateGoodsInfo"
ORDER_URL = 'https://www.hihigo.shop/api/v1/order'
items = {
    '6921168509256001': dict(name='农夫山泉矿泉水', price=2.0, weight=575.0),
    '6956416200067001': dict(name='美汁源果粒橙', price=5.0, weight=487.0),
    '6920202888883001': dict(name='红牛', price=8.0, weight=298.0),
    '6902538006100001': dict(name='脉动', price=6.5, weight=546.0),
    '6921581596048001': dict(name='三得利乌龙茶', price=6.0, weight=528.0),
    '6920459989463001': dict(name='冰糖雪梨', price=6.0, weight=549.0),
    '4891028705949001': dict(name='维他柠檬茶', price=7.0, weight=552.0),
    '6901939621271001': dict(name='雪碧听装', price=3.5, weight=343.0),
    '6901939621608001': dict(name='可口可乐听装', price=3.5, weight=354.0),
    '6925303730574001': dict(name='统一阿萨姆奶茶', price=6.5, weight=550.0),
    '6925303754952001': dict(name='小茗同学黄色', price=6.5, weight=546.0),
    '6925303714857001': dict(name='汤达人豚骨面', price=13.5, weight=184.0),
}

http_port = 5000
sea_key = None

welcome_page = {'D8:9E:F3:1D:E6:9E': 0x33,'D8:9E:F3:1D:EE:7C': 0x0D,'D8:9E:F3:1E:13:8A': 0x33}
WELCOME_PAGE = welcome_page.get(get_mac_address(), 0x33)

SAVE_DEBUG_OUTPUT = False
SAVE_DETECT_OUTPUT = False

#Load basic config corresponding to every different machine.
usb_cameras=[]
from configparser import ConfigParser
config_parser = ConfigParser()
config_parser.read("/home/votance/Projects/Farsight/local/config.ini")

for i in range(4):
    content = config_parser.get("usb_cameras","index"+str(i))
    usb_cameras.append(content)
content = config_parser.get("usb_cameras","index"+str(i))
SAVE_VIDEO_OUTPUT = config_parser.getboolean("maintain_switch","save_video_output")

speaker_on = config_parser.getboolean("maintain_switch","speaker_on")

machine_state = config_parser.get("run_mode","hardware")

logger = Logger(config_parser.get("run_mode","client_mode"))