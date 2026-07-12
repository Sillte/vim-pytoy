import asyncio
from greenlet import greenlet, getcurrent


async def main():
    loop = asyncio.get_running_loop()

    # RPCの応答待ちFuture
    future = loop.create_future()

    def handler():
        print("handler: start")

        current = getcurrent()
        parent = current.parent

        # RPC応答時に呼ばれるコールバック
        def response_callback(fut):
            print("response_callback")
            current.switch(fut.result())

        future.add_done_callback(response_callback)

        print("handler: send request")

        # ---- ここが _yielding_request() 相当 ----
        result = parent.switch()

        print("handler: resumed")
        print("handler: result =", result)
        print("handler: end")

    def func():
        g = greenlet(handler)
        g.switch()

    loop.call_soon_threadsafe(func)
    print("hoghoge")
    loop.call_soon_threadsafe(func)

    print("=== Event A ===")

    print("EventLoopに戻った")

    async def other_event():
        print("=== Event B ===")
        await asyncio.sleep(0.1)
        print("Event B end")

    asyncio.create_task(other_event())

    await asyncio.sleep(0.2)

    print("RPC response arrived")
    future.set_result("Hello")

    await asyncio.sleep(0.2)


asyncio.run(main())
