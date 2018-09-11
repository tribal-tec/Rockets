import asyncio
from rx import Observable, Observer
import websockets

async def _ws_loop(observer):
    ws = await websockets.connect('ws://localhost:8200', subprotocols=['rockets'])
    try:
        async for message in ws:
            observer.on_next(message)
    except Exception as e:
        observer.on_error(e)
    observer.on_completed()

def ws_loop(observer):
    asyncio.get_event_loop().run_until_complete(_ws_loop(observer))

class MessageHandler(Observer):

    def on_next(self, value):
        print("Received {0}".format(value))

    def on_error(self, error):
        print("Error Occurred: {0}".format(error))

rpc_client = Observable.create(ws_loop).filter(lambda value: not isinstance(value, (bytes, bytearray, memoryview)))

rpc_client.subscribe(MessageHandler())
