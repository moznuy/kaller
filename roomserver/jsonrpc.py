import asyncio
import logging
from pprint import pprint
from typing import Dict, Awaitable

from .protocol import ReaderWriterBase

logger = logging.getLogger(__name__)
requests: Dict[int, asyncio.Future] = {}


class JSONRpcException(Exception):
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg

    def __str__(self):
        return f'JSONRpcException ({self.code}): {self.msg}'


async def handle_event_response(result: Dict):
    print(result)


class JsonRPC(ReaderWriterBase):
    async def on_message(self, msg):
        # logger.debug('media_server received %s', str(item))
        try:
            # if not item:
            #     logger.debug('media_server_sender Received End')
            #     break
            item = msg
            r_id = item.get('id')
            if r_id is None:
                if item.get('method') == 'onEvent':
                    await handle_event_response(item)
                else:
                    logger.error('I dont know what to do: %s', item)
                    pprint(item)
                return

            if r_id not in requests:
                logger.error("Unknown response: %s", str(item))
                return

            future = requests[r_id]
            if 'error' in item:
                future.set_exception(JSONRpcException(item['error']['code'], item['error']['message']))
            elif 'result' in item:
                future.set_result(item['result'])
            else:
                logger.error('UNHADLED: %s', str(item))
        except Exception:
            logger.exception('!')


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
    requests[request['id']] = asyncio.Future()
    out_q.put_nowait(request)
    return requests[request['id']]




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
