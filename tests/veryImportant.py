def authorize_operator(self):
        '''
            配货员授权开门，此时：

            - unlock 两边的锁
            - 不进入购物逻辑（不启动摄像头等）
            - 检测是否开门

            如果配货员没有在超时前打开任何一个门，则门会被自动锁上，回到 standby 状态
            如果配货员在超时前只打开了一个门，则另一个门会被自动锁上，唯一打开的方式是关门重新授权
            如果配货员同时打开了两边门，则没事
        '''
        # 更新状态机
        self.restock_authorize_success()

        # 同时打开两边门锁
        self.IO.unlock(self.IO.doorLock.LEFT_DOOR)

        self.IO.unlock(self.IO.doorLock.RIGHT_DOOR)

        # 开始检测是否已经开门
        tornado.ioloop.IOLoop.current().call_later(delay=1, callback=self._check_door_open_by_operator)

    def _check_door_open_by_operator(self, remaining_times=8):
        '''
            检查门是否被配货员打开
        '''
        if remaining_times <= 0:
            # 已经检查足够多次，重置状态机，并且直接返回
            print('超时未开门')
            self.door_open_timed_out()
            print(self.state)
            return

        if self.IO.both_door_closed():
            # 重启检测
            door_check = functools.partial(self._check_door_open_by_operator, remaining_times-1)
            tornado.ioloop.IOLoop.current().call_later(delay=1, callback=door_check)
        else:
            self.restock_open_door_success()

            self.logger.info('配货员已经打开门')

            self.check_door_close_callback = tornado.ioloop.PeriodicCallback(self._check_door_close_by_operator, 300)
            self.check_door_close_callback.start()

    def _check_door_close_by_operator(self):
        '''
            检查门是否被配货员关上
            要同时检测两边门是否都关上
        '''
        if self.IO.both_door_closed():
            self.restock_success()
            self.logger.info(self.state)

            self.logger.info('配货员已经关上门')
            self.check_door_close_callback.stop()