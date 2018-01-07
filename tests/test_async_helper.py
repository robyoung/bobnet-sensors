import asyncio
import threading

from bobnet_sensors.async_helper import (
    StopEvent, Queue
)


def test_stopping(looper):
    assert not looper.stopping
    looper.stop()
    assert looper.stopping


def test_stopping_loop(looper):
    async def run_until_stop(looper):
        while not looper.stopping:
            await looper.stop_event.wait_async()

    async def wait_and_then_stop(looper):
        await asyncio.sleep(0.0001)
        looper.stop()

    looper.loop.run_until_complete(
        asyncio.gather(
            run_until_stop(looper),
            wait_and_then_stop(looper),
            loop=looper.loop
        )
    )


def test_queue_async_put_async_get(loop):
    stop_event = StopEvent(loop)
    queue = Queue(loop, stop_event)

    answers = []

    async def get_with_stop(queue):
        answers.append(await queue.get())
        answers.append(await queue.get())

    async def feeder(queue):
        await queue.put('one')
        await asyncio.sleep(0.001)
        queue.stop_event.stop()
        await queue.put('two')

    loop.run_until_complete(
        asyncio.gather(
            get_with_stop(queue),
            feeder(queue),
            loop=loop
        )
    )

    assert answers == ['one', None]


def test_queue_sync_put_async_get(loop):
    stop_event = StopEvent(loop)
    queue = Queue(loop, stop_event)

    answers = []

    async def get(queue):
        answers.append(await queue.get())

    def feeder():
        queue.sync_put('one')

    def run_loop():
        loop.run_until_complete(
            get(queue),
        )

    thread1 = threading.Thread(target=run_loop)
    thread1.start()
    thread2 = threading.Thread(target=feeder)
    thread2.start()
    thread1.join()
    thread2.join()

    assert answers == ['one']
