import requests
from utils import get_mac_address

mock_door = False
mock_speaker = False
mock_scale = False
mock_screen = False
scale_port = 'COM1'
num_cameras = 4
http_port = 5000

door_time_out=150#

mac_welcome_page = {'D8:9E:F3:1D:E6:9E': 0x33,
                    'D8:9E:F3:1D:EE:7C': 0x0D,
                    'D8:9E:F3:1E:13:8A': 0x0E}

WELCOME_PAGE = mac_welcome_page.get(get_mac_address(), 0x33)

if WELCOME_PAGE == 'error':
    print('mac address is wrong')

usb_cameras=["/dev/v4l/by-path/pci-0000:00:14.0-usb-0:10:1.0-video-index0",
"/dev/v4l/by-path/pci-0000:00:14.0-usb-0:9:1.0-video-index0",
"/dev/v4l/by-path/pci-0000:00:14.0-usb-0:6:1.0-video-index0",
"/dev/v4l/by-path/pci-0000:00:14.0-usb-0:8:1.0-video-index0"
]

items={}

init_url = "https://www.hihigo.shop/api/v1/updateGoodsInfo"

SAVE_OUTPUT = False
