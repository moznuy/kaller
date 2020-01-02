import asyncio
import logging
from pprint import pprint
from typing import Dict, Awaitable, Optional, Tuple

from roomserver.protocol import ReaderWriterBase

logger = logging.getLogger(__name__)


class JSONRpcException(Exception):
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg

    def __str__(self):
        return f'JSONRpcException ({self.code}): {self.msg}'


class EventHandlerInterface:
    async def handle_event_response(self, result: Dict):
        raise NotImplementedError


class SessionInterface:
    def set_session_id(self, s_id: str):
        raise NotImplementedError


class JsonRPCProtocol(ReaderWriterBase):
    def __init__(self, transport, base: 'JsonRPCBase'):
        super().__init__(transport)
        self.base = base
        self.event_handler: Optional[EventHandlerInterface] = None
        self.s_i: Optional[SessionInterface] = None

    def set_callbacks(self, event_handler: EventHandlerInterface, s_i: SessionInterface):
        self.event_handler = event_handler
        self.s_i = s_i

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
                    if self.event_handler:
                        await self.event_handler.handle_event_response(item)
                    else:
                        logger.warning('Received event: % but Event Handler is not set')
                else:
                    logger.error('I dont know what to do: %s', item)
                    pprint(item)
                return

            if not self.base.request_with_id_exist(r_id):
                logger.error("Unknown response: %s", str(item))
                return

            future = self.base.request_with_id(r_id)
            if 'error' in item:
                future.set_exception(JSONRpcException(item['error']['code'], item['error']['message']))
            elif 'result' in item:
                if 'sessionId' in item['result']:
                    self.s_i.set_session_id(item['result'].pop('sessionId'))
                future.set_result(item['result'])
            else:
                logger.error('UNHADLED: %s', str(item))
        except Exception:
            logger.exception('!')


class JsonRPCBase:
    def __init__(self):
        self._json_id: int = 0
        self._requests: Dict[int, asyncio.Future] = {}

    @property
    def incrementing_id(self):
        self._json_id += 1
        return self._json_id

    def _json_request(self, _id, method: str, params: Dict):
        return {
            "id": _id,
            "method": method,
            "params": params,
            "jsonrpc": "2.0"
        }

    def request_with_id_exist(self, r_id) -> bool:
        return r_id in self._requests

    def request_with_id(self, r_id) -> asyncio.Future:
        return self._requests[r_id]

    def create_request(self, method: str, params: Dict, session_id: Optional[int] = None) -> Tuple[Dict, Awaitable]:
        r_id = self.incrementing_id
        self._requests[r_id] = asyncio.Future()
        if session_id is not None:
            params['sessionId'] = session_id
        return self._json_request(r_id, method, params), self._requests[r_id]


class KurentoSession(EventHandlerInterface, SessionInterface):
    session_id: Optional[str] = None

    async def handle_event_response(self, result: Dict):
        print(result)

    def __init__(self, protocol: JsonRPCProtocol):
        self.protocol = protocol
        self.protocol.set_callbacks(self, self)

    def set_session_id(self, s_id: str):
        if self.session_id is not None:
            if self.session_id != s_id:
                logger.warning('Trying to set different Session ID')
            return
        self.session_id = s_id

    async def send_request(self, method: str, params: Dict) -> Awaitable:
        # TODO: hide behind abstraction
        request, future = self.protocol.base.create_request(method, params, self.session_id)
        await self.protocol.transport.send_message(request)
        return future
