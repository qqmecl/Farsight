# -*- coding: utf-8 -*-

import os
import sys
import time
import signal
import subprocess


from spre import Daemon

class MyTestDaemon(Daemon):
    def run(self):
        signal.signal(signal.SIGUSR1, self.__postHandle)
        subprocess.call('/home/votance/anaconda3/bin/python /home/votance/Projects/Farsight/main.py', shell=True)
        sys.stdout.write(sys.path[0])
        while True:
            sys.stdout.write('Daemon Alive! {}\n'.format(time.ctime()))
            sys.stdout.flush()
            time.sleep(5)

    @staticmethod
    def __postHandle(signum, frame):
    	sys.stdout.write('ccccccccc')
    	subprocess.call(['pkill', 'farsight'])
    	time.sleep(2)
    	subprocess.call(['/home/votance/anaconda3/bin/python', '/home/votance/Projects/Farsight/main.py'])
    	sys.stdout.write('tttttttttt')

if __name__ == '__main__':
    PIDFILE = '/tmp/daemon.pid'
    LOG = '/tmp/daemon.log'
    daemon = MyTestDaemon(pidfile=PIDFILE, stdout=LOG, stderr=LOG)

    if len(sys.argv) == 1:
        print('Usage: {} [start|stop] but success already'.format(sys.argv[0]), file=sys.stderr)
        daemon.start()

    else:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print('Unknown command {!r}'.format(sys.argv[1]), file=sys.stderr)
            raise SystemExit(1)
