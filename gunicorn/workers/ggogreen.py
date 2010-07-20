# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license.
# See the NOTICE for more information.

import contextlib

from gogreen import coro

coro.socket_emulate()

from gunicorn.workers.async import AsyncWorker


class GogreenWorker(AsyncWorker):
    def run(self):
        acceptor = AcceptorThread(args=(self,))
        acceptor.start()
        coro.event_loop()

    @contextlib.contextmanager
    def timeout_ctx(self):
        yield


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
