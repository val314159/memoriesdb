import asyncio
import websockets

async def hello_client():
    async with websockets.connect("ws://localhost:8765/ws?ch=qwe-rt,y-uiop") as websocket:
        await websocket.send("Hello, server!")
        response = await websocket.recv()
        print(f"Received from server: {response}")
        pass
    pass

if __name__ == "__main__":
    asyncio.run(hello_client())
