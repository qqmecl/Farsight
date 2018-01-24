mock_door = False
mock_speaker = False
mock_scale = False
mock_screen = False
scale_port = 'COM1'
num_cameras = 4
http_port = 5000

WELCOME_PAGE = 0x0E
# WELCOME_PAGE = 0x33
usb_cameras=["/dev/v4l/by-path/pci-0000:00:14.0-usb-0:10:1.0-video-index0",
"/dev/v4l/by-path/pci-0000:00:14.0-usb-0:9:1.0-video-index0",
"/dev/v4l/by-path/pci-0000:00:14.0-usb-0:6:1.0-video-index0",
"/dev/v4l/by-path/pci-0000:00:14.0-usb-0:8:1.0-video-index0"
]

#旧方式下的随机id体系
items = {
    '001001': dict(name='农夫山泉矿泉水', price=1.0, weight=575.0),
    '002004': dict(name='美汁源果粒橙', price=5.0, weight=487.0),
    '006001': dict(name='红牛', price=8.0, weight=298.0),
    '007001': dict(name='脉动', price=6.5, weight=546.0),
    '008001': dict(name='三得利乌龙茶', price=6.0, weight=528.0),
    '009001': dict(name='冰糖雪梨', price=6.0, weight=549.0),
    '010001': dict(name='维他柠檬茶', price=7.0, weight=552.0),
    '002001': dict(name='雪碧听装', price=3.5, weight=343.0),
    '002002': dict(name='可口可乐听装', price=3.5, weight=354.0),
    '003001': dict(name='统一阿萨姆奶茶', price=6.5, weight=550.0),
    '003002': dict(name='小茗同学黄色', price=6.5, weight=546.0),
    '003003': dict(name='汤达人豚骨面', price=13.5, weight=184.0),
}

# TODO: 改成从服务器获取，或者从本地文件读取
#新方式下，统一使用条形码对应的id
# items = {
#     '6921168509256': dict(name='农夫山泉矿泉水', price=2.0, weight=575.0),
#     '6956416200067': dict(name='美汁源果粒橙', price=5.0, weight=487.0),
#     '6920202888883': dict(name='红牛', price=8.0, weight=298.0),
#     '6902538006100': dict(name='脉动', price=6.5, weight=546.0),
#     '6921581596048': dict(name='三得利乌龙茶', price=6.0, weight=528.0),
#     '6920459989463': dict(name='冰糖雪梨', price=6.0, weight=549.0),
#     '4891028705949': dict(name='维他柠檬茶', price=7.0, weight=552.0),
#     '6901939621271': dict(name='雪碧听装', price=3.5, weight=343.0),
#     '6901939621608': dict(name='可口可乐听装', price=3.5, weight=354.0),
#     '6925303730574': dict(name='统一阿萨姆奶茶', price=6.5, weight=550.0),
#     '6925303754952': dict(name='小茗同学(黄色)', price=6.5, weight=546.0),
#     '6925303714857': dict(name='汤达人豚骨面(碗装)', price=13.5, weight=184.0),
# }
