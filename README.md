# 远瞳智能工控机管理系统

http://www.votance.com/

## 功能简介

该程序作为工控机的管理程序，维护一个状态机，合理控制附属的几个I/O设备。

主程序所控制的I/O设备包括：若干个摄像头，一个显示屏幕，一个扬声器和门控设备(集成在一起)，若干个传感器设备。

主设备与从设备之间通过modbus协议进行通讯。

程序所管理状态机分为三个主要阶段，休眠模式 --> 开门(来回存取物件模式)调用识别检测(返回结果) --> 关门(结算休眠)-->继续循环

程序语言为 Python 3.

## 代码结构

程序主入口在 `main.py` 中，详细启动参数参见 `main.py` 文件。

程序正常工作需要连接摄像头、门和锁（通过串口通信）、扬声器（通过串口通信）、重量计（通过串口通信），

其中摄像头数量可以通过启动参数配置，所有串口设备都可以 MOCK 掉。

主要文件：

- `closet.py` 是售货柜的模型，使用 `transitions` 库进行状态机建模。运行在主线程中。
- `httpd.py` 是基于 `Tornado` 的 HTTP 接口，用于接收中央系统（云服务）的通信指令。运行在主线程中。
- `object_detector.py` 是物品识别和手势识别算法的实现（基于 TensorFlow Object Detection API）
- `selfcheck.py` 是自检程序
- `visualize.py` 是开发中的可视化检测辅助程序
- `serial_handler` 目录是所有串口通信相关代码的模块
- `cart.py` 是虚拟购物车

## 程序运行逻辑

程序运行时，由以下若干个进程组成：

- [farsight] 主进程 (x1)
- [farsight] 摄像头发送帧进程 (x1)
- [farsight] TensorFlow 图像处理进程 (x 摄像头数量 x 每摄像头对应 worker 数，默认是 4x1 共 4 个)

主进程的主线程是一个 `tornado.ioloop.IOLoop` 实例，使用 `Tornado` 的异步 IO 体系，

把各种外部输入（HTTP 请求，传感器输入比如关门操作等）统一接入在一个线程中处理，对其他子进程的控制通过发送消息来进行，

简化了主程序逻辑，避免了资源竞争和各种 race condition.

### 进程结构图

```
+----------+                        +----------+
|          |                        |  camera  |
|   main   |                        |  input   |
| process  |--------ctrl_queue----->| handler  |
|          |                        | process  |
+----------+                        +----------+
      ^                                   |
      |                                frame
      |                                input
      |                                queues
      |                                   |
      |                              +----v-----+
      |                             ++---------+|
      |                             |          ||
      |                             |  object  ||
      +----detection_queue----------| detector ||
                                    | process  ||
                                    |          ++
                                    +----------+
```

### 启动过程

程序启动后，先进行自检，然后 spawn 出一个摄像头发送帧进程和若干个 TensorFlow 图像处理进程，

这些子进程全部进入 standby 状态，而主进程启动 `Tornado` 的 `IOLoop`，准备接受 HTTP 请求，请求可能为：

- 用户扫码授权（已实现）
- 运营方补货
- 中央系统（云服务）获取主机状态

理想状态下，在空闲时这些进程占用的总 CPU 应该低于 10%。

#### 启动过程示意图（standby 状态）

```
+----------+                       +-------+
|boot phase|   +----------+        |standby|       +----------+
+----------+   |          |        +-------+       |  camera  |
               |   main   |                        |  input   |
               | process  |--------ctrl_queue----->| handler  |
               |          |                        | process  |
               +----------+                        +----------+
                     ^                                   |
                     |                                frame   +-------+
                     |                                input   | empty |
                     |                                queues  +-------+
                     |                                   |
                     |                              +----v-----+
                     |                             ++---------+|
                     |                             |          ||
                     |                             |  object  ||
                   detection_queue-----------------| detector ||
                                                   | process  ||
                                                   |          ++
                                                   +----------+
```

### 工作状态（物体识别中）

当主进程收到用户扫码授权请求之后，给摄像头发送帧进程发送指令消息，此时该进程进入繁忙工作状态，

且和开门侧对应的摄像头的 TensorFlow 图像处理进程也进入繁忙工作状态。

此时所有进程占用的总 CPU 可能超过 80%。

当 TensorFlow 进程识别到物体和用户的操作（拿进或者拿出），发送消息进入 `detection_queue`

#### 工作状态示意图

```
+----------+                       +-------+
| working  |   +----------+        | start |       +----------+
|  phase   |   |          |        +-------+       |  camera  |
+----------+   |   main   |                        |  input   |
        +----->| process  |--------ctrl_queue----->| handler  |
        |      |          |                        | process  |
        |      +----------+                        +----------+
   authorize         ^                                   |
        |            |                                frame   +------+
        |            |                                input   |frames|
        |            |                                queues  +------+
  +----------+       |                                   |
  |          |       |                              +----v-----+
  | farsight |       |    +-----------+            ++---------+|
  |  cloud   |       |    |user action|            |          ||
  |          |       |    +-----------+            |  object  ||
  +----------+     detection_queue-----------------| detector ||
                                                   | process  ||
                                                   |          ++
                                                   +----------+
```

### 结算订单流程

当主进程检测到用户关门，进入结算订单流程。主进程发送 `stop` 指令给摄像头控制进程，随着摄像头帧队列的清空，

TensorFlow 进程也因为饥饿进入等待状态。

#### 结算订单流程示意图

```

         door closed--+
             |        |
+----------+ |        |             +------+
| checkout | |  +----------+        | stop |        +----------+
|  phase   | |  |          |        +------+        |  camera  |
+----------+ |  |   main   |                        |  input   |
             +->| process  |--------ctrl_queue----->| handler  |
                |          |                        | process  |
                +----------+                        +----------+
                  |   ^                                   |
       checkout---+   |                                frame   +-------+
        |             |                                input   | empty |
        v             |                                queues  +-------+
  +----------+        |                                   |
  |          |        |                              +----v-----+
  | farsight |        |    +-----------+            ++---------+|
  |  cloud   |        |    |   empty   |            |          ||
  |          |        |    +-----------+            |  object  ||
  +----------+      detection_queue-----------------| detector ||
                                                    | process  ||
                                                    |          ++
                                                    +----------+
```

### 使用多进程架构的设计思路

- 为了简化主线程逻辑，强化状态机模型，避免资源竞争
- 确保在用户扫码之后有足够快的响应速度
- 尽可能多地利用工控机系统资源，并且保证在空闲时资源占用足够小

## 开发设置

### git clone 代码

    git clone git@github.com:mutanio/farsight.git

### 拷贝模型至 data 目录下

`pascal_label_map.pbtxt` 和 `frozen_inference_graph.pb`

### 安装依赖

    conda env create -f environment.yml

### 进入 conda env

    source activate farsight

## 部署设置

安装 Anaconda3-5.0.0.1-Linux-x86_64.sh (网络下载或移动硬盘拷贝),配置好 opencv 和 python 3.6 开发环境

### 单独测试各个串口设备连接性问题

    部署软件到工控机一般过程:

    1.确保网管配置好工控机的ssh服务器及花生壳域名

    2.安装 环境配置/Miniconda3-latest-Linux-x86_64.sh

    3.使用pip install pyserial transitions setproctitle tornado opencv-python

    4.串口问题 Ubuntu 串口权限默认 owner 是 root， group 是 dialout，所以一个访问串口的方式是，把当前用户加入 dialout 组: sudo usermod votance -G dialout

    5.进入serial/handler中，测试每一个串口设备的连通性，累计执行 python screen.py; python scale.py; python speaker.py; python door_lock.py;确认完毕之后，执行步骤5

    6.执行python main.py 测试主进程是否正常运行.


运行自动配置脚本 setup/install.sh

安装好库依赖

### 串口问题

Ubuntu 串口权限默认 owner 是 `root`， group 是 `dialout`，所以一个访问串口的方式是，把当前用户加入 `dialout` 组:

    sudo usermod votance -G dialout

需要注销重新登录（或者在终端 `su -l votance`）才能让设置生效

### 摄像头问题

在同时接了四个摄像头的机器上运行程序可能会遇到 `no space left on device` 错误，该错误的原因是每个摄像头请求过多总线带宽。

参照这篇文章进行以下设置即可解决问题

http://renoirsrants.blogspot.in/2011/07/multiple-webcams-on-zoneminder.html

    sudo rmmod uvcvideo

    sudo modprobe uvcvideo quirks=128

确保重启之后设置仍然生效，编辑

    sudo vi /etc/modprobe.d/uvcvideo.conf

添加

    options uvcvideo quirks=128

即可。

## 串口端口配置
门锁 和 喇叭 共用 COM1 口
屏幕用 COM0 口
压力传感器 用 COM4 口
