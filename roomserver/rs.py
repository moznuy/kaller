import asyncio
import logging
from asyncio import Future
from contextlib import suppress
from pprint import pprint
from typing import Dict, Awaitable

import aiohttp
from aiohttp import web

from roomserver.jsonrpc import JsonRPC, send_custom_request
from roomserver.media.pipeline import MediaPipeline
from roomserver.media.session import KurentoSession, JsonRPCProtocol, JsonRPCBase
from roomserver.media.web_rtc_endpoint import WebRTCEndPoint
from roomserver.protocol import ReaderWriterBase
from roomserver.runner import run_app
from roomserver.transport import WebSocketResponse, WebSocketBase, WebSocketClient

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)40s - %(levelname)9s - %(message)s')
logger = logging.getLogger('rs')


class Echo(ReaderWriterBase):
    async def on_message(self, msg):
        await self.transport.send_message({'resp': 1})


async def websocket_handler(request):
    async with WebSocketResponse(request, raw=True) as response:
        async with Echo(response):
            await response.run()
        # while True:
        #     await response.run(timeout=0.1)
        #     print('loop')
    print('websocket connection closed')
    return response.ws


# async def media_server_sender(socket: aiohttp.ClientWebSocketResponse, q: asyncio.Queue):
#     need_to_fetch = True
#     try:
#         while True:
#             item = await q.get()
#             try:
#                 if not item:
#                     logger.debug('media_server_sender Received End')
#                     break
#                 logger.debug('media_server_sender sending %s', str(item))
#                 await socket.send_json(item)
#             finally:
#                 q.task_done()
#     except asyncio.CancelledError:
#         logger.debug('media_server_sender Canceled')
#     else:
#         need_to_fetch = False
#     finally:
#         if not need_to_fetch:
#             return
#         while True:
#             item = await q.get()
#             q.task_done()
#             if not item:
#                 break

# TODO: global in app
rpc_base = JsonRPCBase()

async def media_server(app):
    try:
        async with WebSocketClient('ws://127.0.0.1:8888/kurento') as client:
            async with JsonRPCProtocol(client, rpc_base) as protocol:
                session = KurentoSession(protocol)
                p = MediaPipeline(session)
                await p.create()
                wb = WebRTCEndPoint(p, session)
                await wb.create()
                try:
                    await client.run()
                except asyncio.CancelledError:
                    logger.debug('media_server Canceled')
                finally:
                    logger.debug('media_server Finished')
    except Exception:
        logger.exception('!!!!!!')


# async def media_server(app):
#     try:
#         async with WebSocketClient('ws://127.0.0.1:8888/kurento') as client:
#             logger.debug('Connected')
#             async with JsonRPC(client):
#                 ccc = asyncio.create_task(send_custom_request(client.outbound_queue))
#                 try:
#                     await client.run()
#                 except asyncio.CancelledError:
#                     logger.debug('media_server Canceled')
#                 finally:
#                     ccc.cancel()
#                     await ccc
#                     logger.debug('media_server Finished')
#     except Exception:
#         logger.exception('!!!!!!')

# async def media_server(app):
#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.ws_connect('ws://127.0.0.1:8888/kurento') as socket:  # TODO: retrygit log\
#                 logger.debug('Connected')
#                 q = asyncio.Queue()
#                 i_q = asyncio.Queue()
#                 t = asyncio.create_task(media_server_sender(socket, q))
#                 j = asyncio.create_task(json_rpc_handler(i_q, q))
#                 ccc = asyncio.create_task(send_custom_request(q))
#                 try:
#                     async for msg in socket:  # type: aiohttp.WSMessage
#                         await i_q.put(msg.json())
#                 except asyncio.CancelledError:
#                     logger.debug('media_server Canceled')
#                 finally:
#                     # if app['gunicorn']:
#                     j.cancel()
#                     await j
#                     await q.put(None)
#                     await q.join()
#                     await t
#                     logger.debug('media_server Finished')
#     except Exception:
#         logger.exception('!!!!!!')


async def start_background_tasks(app):
    logger.debug('Start')
    app['media_server'] = asyncio.create_task(media_server(app))


async def cleanup_background_tasks(app):
    logger.debug('Stop')
    # if app['gunicorn']:

    app['media_server'].cancel()
    await app['media_server']

    logger.debug('Stopped')


async def shutdown_runners(app):
    WebSocketBase.cancel_runners()


app = web.Application()
app.add_routes([web.get('/ws', websocket_handler)])
app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)
app.on_shutdown.append(shutdown_runners)
# app.setdefault('gunicorn', True)

if __name__ == '__main__':
    # app['gunicorn'] = False
    # asyncio.get_event_loop().set_debug(True)
    with suppress(asyncio.CancelledError):
        run_app(app)
