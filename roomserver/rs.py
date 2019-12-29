import asyncio
import logging
from asyncio import Future
from contextlib import suppress
from pprint import pprint
from typing import Dict, Awaitable

import aiohttp
from aiohttp import web

from roomserver.runner import run_app

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('rs')


async def websocket_handler(request):

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:  # type: aiohttp.WSMessage
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
            else:
                await ws.send_str(msg.data + '/answer')
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' %
                  ws.exception())

    print('websocket connection closed')

    return ws


async def media_server_sender(socket: aiohttp.ClientWebSocketResponse, q: asyncio.Queue):
    need_to_fetch = True
    try:
        while True:
            item = await q.get()
            try:
                if not item:
                    logger.debug('media_server_sender Received End')
                    break
                logger.debug('media_server_sender sending %s', str(item))
                await socket.send_json(item)
            finally:
                q.task_done()
    except asyncio.CancelledError:
        logger.debug('media_server_sender Canceled')
    else:
        need_to_fetch = False
    finally:
        if not need_to_fetch:
            return
        while True:
            item = await q.get()
            q.task_done()
            if not item:
                break


requests: Dict[int, Future] = {}


class JSONRpcException(Exception):
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg

    def __str__(self):
        return f'JSONRpcException ({self.code}): {self.msg}'


async def json_rpc_handler(in_q: asyncio.Queue, out_q: asyncio.Queue):
    try:
        while True:
            item = await in_q.get()  # type: Dict
            # logger.debug('media_server received %s', str(item))
            try:
                # if not item:
                #     logger.debug('media_server_sender Received End')
                #     break
                r_id = item.get('id')
                if r_id is None:
                    if item.get('method') == 'onEvent':
                        await handle_event_response(item)
                    else:
                        logger.error('I dont know what to do: %s', item)
                        pprint(item)
                    continue

                if r_id not in requests:
                    logger.error("Unknown response: %s", str(item))
                    continue

                future = requests[r_id]
                if 'error' in item:
                    future.set_exception(JSONRpcException(item['error']['code'], item['error']['message']))
                elif 'result' in item:
                    future.set_result(item['result'])
                else:
                    logger.error('UNHADLED: %s', str(item))
            finally:
                in_q.task_done()
    except asyncio.CancelledError:
        pass

JSON_ID = 0


def json_id():
    global JSON_ID
    JSON_ID += 1
    return JSON_ID


def json_request(method: str, params: Dict):
    return {
        "id": json_id(),
        "method": method,
        "params": params,
        "jsonrpc": "2.0"
    }


def json_rpc_custom_request(out_q: asyncio.Queue, method: str, params: Dict) -> Awaitable:
    request = json_request(method, params)
    requests[request['id']] = Future()
    out_q.put_nowait(request)
    return requests[request['id']]


async def handle_event_response(result: Dict):
    print(result)


async def send_custom_request(out_q: asyncio.Queue):
    try:
        result = await json_rpc_custom_request(out_q, method="create", params={
            "type": "MediaPipeline",
            "constructorParams": {},
            "properties": {}
        })
    except Exception:
        logger.exception('COMMAND: ')
        return
    else:
        logger.info("MediaPipeline: %s", str(result))

    session_id = result['sessionId']
    pipeline_id = result['value']

    try:
        result = await json_rpc_custom_request(out_q, method="create", params={
            "type": "WebRtcEndpoint",
            "constructorParams": {
                "mediaPipeline": pipeline_id
            },
            "properties": {},
            "sessionId": session_id
        })
    except Exception:
        logger.exception('COMMAND: ')
        return
    else:
        logger.info("WebRtcEndpoint: %s", str(result))

    webrtc_endpoint = result['value']

    try:
        result = await json_rpc_custom_request(out_q, method="invoke", params={
            "object": webrtc_endpoint,
            "operation": "connect",
            "operationParams": {
                "sink": webrtc_endpoint
            },
            "sessionId": session_id
        })
    except Exception:
        logger.exception('COMMAND: ')
        return
    else:
        logger.info("WebRtcEndpoint connect loopback: %s", str(result))

    try:
        result = await json_rpc_custom_request(out_q, method="subscribe", params={
            "type": "IceCandidateFound",
            "object": webrtc_endpoint,
            "sessionId": session_id
        })
    except Exception:
        logger.exception('COMMAND: ')
        return
    else:
        logger.info("WebRtcEndpoint subscribe: %s", str(result))

    sbs_id = result['value']

    try:
        result = await json_rpc_custom_request(out_q, method="invoke", params={
            "object": webrtc_endpoint,
            "operation": "generateOffer",
            "operationParams": {
                # "offer": "SDP"
            },
            "sessionId": session_id
        })
    except Exception:
        logger.exception('COMMAND: ')
        return
    else:
        logger.info("WebRtcEndpoint generateOffer: %s", str(result))

    try:
        result = await json_rpc_custom_request(out_q, method="invoke", params={
            "object": webrtc_endpoint,
            "operation": "gatherCandidates",
            "operationParams": {},
            "sessionId": session_id
        })
    except Exception:
        logger.exception('COMMAND: ')
        return
    else:
        logger.info("WebRtcEndpoint gatherCandidates: %s", str(result))






async def media_server(app):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect('ws://127.0.0.1:8888/kurento') as socket:  # TODO: retrygit log\
                logger.debug('Connected')
                q = asyncio.Queue()
                i_q = asyncio.Queue()
                t = asyncio.create_task(media_server_sender(socket, q))
                j = asyncio.create_task(json_rpc_handler(i_q, q))
                ccc = asyncio.create_task(send_custom_request(q))
                try:
                    async for msg in socket:  # type: aiohttp.WSMessage
                        await i_q.put(msg.json())
                except asyncio.CancelledError:
                    logger.debug('media_server Canceled')
                finally:
                    # if app['gunicorn']:
                    j.cancel()
                    await j
                    await q.put(None)
                    await q.join()
                    await t
                    logger.debug('media_server Finished')
    except Exception:
        logger.exception('!!!!!!')


async def start_background_tasks(app):
    logger.debug('Start')
    app['media_server'] = asyncio.create_task(media_server(app))


async def cleanup_background_tasks(app):
    logger.debug('Stop')
    # if app['gunicorn']:
    app['media_server'].cancel()
    await app['media_server']
    logger.debug('Stopped')


app = web.Application()
app.add_routes([web.get('/ws', websocket_handler)])
app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)
# app.setdefault('gunicorn', True)

if __name__ == '__main__':
    # app['gunicorn'] = False
    with suppress(asyncio.CancelledError):
        run_app(app)
