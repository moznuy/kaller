import asyncio
import logging
from asyncio import Task
from typing import Optional, Union, Dict, Iterable, Set

import aiohttp
from aiohttp import web
from aiohttp.client import _WSRequestContextManager

logger = logging.getLogger(__name__)


def results_dispose(tasks: Iterable[Task]):
    for task in tasks:
        try:
            task.result()
        except asyncio.CancelledError:
            logger.debug('Task was canceled: %s', task)
        except Exception:
            logger.exception('Task raised: %s', task)


class WebSocketBase:
    ws: Union[web.WebSocketResponse, aiohttp.ClientWebSocketResponse]
    sender_task: Task
    receiver_task: Task
    runners: Set[Task] = set()

    def __init__(self, raw: bool = False):
        self.inbound_queue = asyncio.Queue()
        self.outbound_queue = asyncio.Queue()
        self.raw = raw

    async def sender(self):
        while True:
            item = await self.outbound_queue.get()
            try:
                if not item:
                    logger.debug('media_server_sender Received End')
                    break
                # logger.debug('media_server_sender sending %s', str(item))
                await self.ws.send_json(item)
            finally:
                self.outbound_queue.task_done()

    async def receiver(self):
        async for msg in self.ws:  # type: aiohttp.WSMessage
            # TODO: msg.type == aiohttp.WSMsgType.ERROR:
            await self.inbound_queue.put(msg.json() if not self.raw else msg.data)

    async def send_message(self, data: Dict):
        await self.outbound_queue.put(data)

    async def _run(self, timeout: Optional[float] = None):
        tasks = {self.receiver_task, self.sender_task}
        await asyncio.wait(tasks, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)

    async def run(self, timeout: Optional[float] = None):
        runner = asyncio.create_task(self._run(timeout))
        self.runners.add(runner)
        await asyncio.wait_for(runner, None)
        self.runners.remove(runner)

    @classmethod
    def cancel_runners(cls):
        for runner in cls.runners:
            runner.cancel()

    async def __aenter__(self):
        self.sender_task = asyncio.create_task(self.sender())
        self.receiver_task = asyncio.create_task(self.receiver())

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        tasks = {self.receiver_task, self.sender_task}
        for task in tasks:
            if self.sender_task.done():
                continue
            task.cancel()
        await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
        results_dispose(tasks)


class WebSocketResponse(WebSocketBase):
    def __init__(self, request, **kwargs):
        super().__init__(**kwargs)
        self.request = request

    async def __aenter__(self):
        self.ws = web.WebSocketResponse()
        await self.ws.prepare(self.request)
        await super().__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await super().__aexit__(exc_type, exc_val, exc_tb)


class WebSocketClient(WebSocketBase):
    session: aiohttp.ClientSession
    ws_cm: _WSRequestContextManager

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    async def __aenter__(self):
        self.session = await aiohttp.ClientSession().__aenter__()
        self.ws_cm = self.session.ws_connect(self.url)
        self.ws = await self.ws_cm.__aenter__()
        await super().__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await super().__aexit__(exc_type, exc_val, exc_tb)
        await self.ws_cm.__aexit__(exc_type, exc_val, exc_tb)
        await self.session.__aexit__(exc_type, exc_val, exc_tb)
