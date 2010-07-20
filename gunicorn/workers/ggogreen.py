# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

from gogreen import coro

coro.socket_emulate()

from gunicorn.workers.async import AsyncWorker


class GogreenWorker(AsyncWorker):
    def run(self):
        acceptor = AcceptorThread(args=(self,))
        acceptor.start()
        coro.event_loop()

    def timeout_ctx(self):
        timer = TimerThread(args=(self, self.cfg.keepalive))
        timer.start()
        return timer


class NotifierThread(coro.Thread):
    def run(self, worker):
        while worker.alive:
            worker.notify()
            self.Yield(worker.timeout / 2.0)


class HandlerThread(coro.Thread):
    def run(self, worker, conn, address):
        worker.handle(conn, address)


class AcceptorThread(coro.Thread):
    def run(self, worker):
        notifier = NotifierThread(args=(worker,))
        notifier.start()

        while worker.alive:
            worker.notify()

            conn, address = worker.socket.accept()
            handler = HandlerThread(args=(worker, conn, address))
            handler.start()


class TimerThread(coro.Thread):
    def run(self, worker, seconds):
        self._cancelled = False

        self.Yield(seconds)

        if not self._cancelled:
            worker.timeout()

    def __enter__(self):
        return self

    def __exit__(self, klass, value, tb):
        self._cancelled = True
