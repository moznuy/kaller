import asyncio

from .transport import WebSocketResponse


class ReaderWriterBase:
    def __init__(self, transport: WebSocketResponse):
        self.transport = transport

    async def __aenter__(self):
        self.t = asyncio.create_task(self.run())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.t.cancel()

    async def run(self):
        while True:
            await self.on_message(await self.transport.inbound_queue.get())
            self.transport.inbound_queue.task_done()

    async def on_message(self, msg):
        raise NotImplementedError
