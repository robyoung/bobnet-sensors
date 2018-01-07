import asyncio
import threading

import janus


class StopEvent:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.async_event = asyncio.Event(loop=loop)
        self.sync_event = threading.Event()

    @property
    def stopping(self):
        return self.sync_event.is_set()

    def stop(self):
        self.sync_event.set()
        self.async_event.set()

    def wait_async(self):
        return self.async_event.wait()

    def wait_sync(self, timeout=None):
        return self.sync_event.wait(timeout)


class Looper:
    """Async helper class

    This class is responsible for abstracting shared async primitives and
    common operations.
    """
    loop: asyncio.AbstractEventLoop

    config_queue: janus.Queue
    send_queue: janus.Queue

    stop_event: StopEvent

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.stop_event = StopEvent(loop=loop)
        self.config_queue = Queue(loop, self.stop_event)
        self.send_queue = Queue(loop, self.stop_event)

    @property
    def stopping(self):
        return self.stop_event.stopping

    def stop(self):
        self.stop_event.stop()

    async def wait_for(self, timeout):
        try:
            await asyncio.wait_for(
                self.stop_event.async_event.wait(),
                timeout,
                loop=self.loop
            )
        except asyncio.TimeoutError:
            pass


class Queue:
    def __init__(self,
                 loop: asyncio.AbstractEventLoop,
                 stop_event: StopEvent):
        self.loop = loop
        self.queue = janus.Queue(loop=loop)
        self.stop_event = stop_event

    def sync_put(self, item):
        if not self.stop_event.stopping:
            self.queue.sync_q.put(item)

    async def put(self, item):
        if not self.stop_event.stopping:
            return await self.queue.async_q.put(item)

    async def get(self):
        if not self.stop_event.stopping:
            get_task = self.loop.create_task(
                self.queue.async_q.get()
            )
            stop_task = self.loop.create_task(
                self.stop_event.wait_async()
            )
            complete, pending = await asyncio.wait(
                [get_task, stop_task],
                loop=self.loop, return_when=asyncio.FIRST_COMPLETED
            )
            task = complete.pop()

            if task == get_task:
                stop_task.cancel()
                return get_task.result()
            else:
                get_task.cancel()
