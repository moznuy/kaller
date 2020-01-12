import aiohttp
import asyncio


create_pipeline = {
  "id": 2,
  "method": "create",
  "params": {
    "type": "MediaPipeline",
    "constructorParams": {},
    "properties": {}
  },
  "jsonrpc": "2.0"
}

create_endpoint = {
  "id": 3,
  "method": "create",
  "params": {
    "type": "WebRtcEndpoint",
    "constructorParams": {
      "mediaPipeline": None
    },
    "properties": {},
  },
  "jsonrpc": "2.0"
}

reconnect = {
  "jsonrpc": "2.0",
  "id": 7,
  "method": "connect",
  "params": {
    "sessionId": None
  }
}


async def default(client: aiohttp.ClientWebSocketResponse):
    await client.send_json(create_pipeline)
    ans = await client.receive_json()
    session_id = ans['result']['sessionId']
    pipeline_id = ans['result']['value']
    print(session_id, pipeline_id)

    create_endpoint['params']['constructorParams']['mediaPipeline'] = pipeline_id
    await client.send_json(create_endpoint)
    # exit(1)
    print('asd')
    await asyncio.sleep(1)

    # # await client.
    # return

    ans = await client.receive_json()
    element_id = ans['result']['value']
    print(element_id)


async def rec(client: aiohttp.ClientWebSocketResponse):
    session_id = '1f73ef4e-8482-4951-87a1-4d383e1545f3'
    reconnect['params']['sessionId'] = session_id
    await client.send_json(reconnect)
    ans = await client.receive_json()
    print(ans)
    ans = await client.receive_json()
    print(ans)


async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect('ws://127.0.0.1:8888/kurento') as client:
            # await default(client)
            await rec(client)




if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.set_debug(True)
    t = loop.create_task(main())
    try:
        loop.run_until_complete(t)
    except KeyboardInterrupt:
        t.cancel()
        loop.run_until_complete(t)
        loop.run_until_complete(loop.shutdown_asyncgens())
        asyncio.set_event_loop(None)
        loop.close()

