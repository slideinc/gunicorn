# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

import eventlet
import eventlet.debug

from eventlet.green import os
from eventlet import greenlet
from eventlet import greenpool
from eventlet import greenthread
from eventlet import hubs

from gunicorn.workers.async import AsyncWorker

eventlet.debug.hub_exceptions(True)

class EventletWorker(AsyncWorker):

    @classmethod
    def setup(cls):
        import eventlet
        if eventlet.version_info < (0,9,7):
            raise RuntimeError("You need eventlet >= 0.9.7")
        eventlet.monkey_patch()
    
    def init_process(self):
        hubs.use_hub()
        super(EventletWorker, self).init_process()
        
    def timeout_ctx(self):
        return eventlet.Timeout(self.cfg.keepalive, False)
        
    def run(self):
        self.socket.setblocking(1)

        pool = greenpool.GreenPool(self.worker_connections)
        acceptor = greenthread.spawn(self.acceptor, pool)
        
        while self.alive:
            self.notify()

            if self.cfg.max_connections > 0:
                if self.num_conns > self.cfg.max_connections:
                    self.log.info("Exceeded connection limit. Restarting.")
                    greenthread.kill(acceptor, eventlet.StopServe)
                    break

            if self.ppid != os.getppid():
                self.log.info("Parent changed, shutting down: %s" % self)
                greenthread.kill(acceptor, eventlet.StopServe)
                break
            
            eventlet.sleep(0.1)            

        with eventlet.Timeout(self.timeout, False):
            pool.waitall()

    def acceptor(self, pool):
        greenthread.getcurrent()
        while self.alive:
            try:
                conn, addr = self.socket.accept()
                gt = pool.spawn(self.handle, conn, addr)
                gt.link(self.cleanup, conn)
                conn, addr, gt = None, None, None
            except eventlet.StopServe:
                return
            except:
                self.log.exception("Unexpected error in acceptor. Sepuku.")
                os._exit(4)

    def cleanup(self, thread, conn):
        try:
            try:
                thread.wait()
            finally:
                conn.close()
        except greenlet.GreenletExit:
            pass
        except Exception:
            self.log.exception("Unhandled exception in worker.")

