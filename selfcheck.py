import cv2
from serial_handler.door_lock import DoorError, LockError
from camera_handler import CameraError
import settings

if settings.mock_door:
    from serial_handler.mock import DoorLockHandler
else:
    from serial_handler.door_lock import DoorLockHandler

if settings.mock_scale:
    from serial_handler.mock import WeightScale
else:
    from serial_handler.scale import WeightScale


def selfcheck():
    '''
        跑自检代码，如果失败了，报错并且在屏幕上显示异常信息
        TODO: 移植原来的 check.py 代码
    '''
    check_door_and_lock()
    check_cameras()
    check_weight_scale()

    return True


def check_door_and_lock():
    '''
        检测门和锁的状态
    '''
    door_handler = DoorLockHandler()

    if not door_handler.both_lock_locked():
        # TODO: 尝试 reset 锁
        raise LockError('锁没有全锁上')

    if not door_handler.both_door_closed():
        raise DoorError('门没有全关上')

    return True


def check_cameras():
    '''
        检查需要一共有四个摄像头，并且每个摄像头工作良好
    '''
    for i in range(settings.num_cameras):
        camera = cv2.VideoCapture(i)
        if not camera.isOpened():
            raise CameraError("摄像头 {0} 没有准备好".format(i))
        camera.release()

    return True


def check_weight_scale():
    '''
        检查重力计是否正常工作
    '''
    scale = WeightScale(settings.scale_port)
    if scale.read() <= 0:
        raise WeightScaleError('重力计没有正常工作')

    return True


if __name__ == '__main__':
    # settings.num_cameras = 1
    print(check_weight_scale())
