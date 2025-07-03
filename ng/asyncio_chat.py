#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import aiohttp
from typing import Optional, Dict, Any

# Environment variables
CH = os.getenv('CH', 'llm')
CH_IN = os.getenv('CH_IN', f'{CH}-in')
CH_OUT = os.getenv('CH_OUT', f'{CH}-out')
CHANNELS = [CH_OUT]
WS_BASE = "ws://localhost:5002/ws"
WS_ARGS = '?c=' + '&c='.join(CHANNELS)
WS_URL = f"{WS_BASE}{WS_ARGS}"

def mesg(method: str, **params) -> Dict[str, Any]:
    """Create a message dictionary with method and parameters."""
    return {"method": method, "params": params}

async def pub(ws: aiohttp.ClientWebSocketResponse, channel: str, content: str = '', **kw) -> None:
    """Publish a message to a channel."""
    message = mesg('pub', channel=channel, content=content, **kw)
    await ws.send_str(json.dumps(message))

async def read_stdin() -> Optional[str]:
    """Read a line from stdin asynchronously."""
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    
    while True:
        print("user> ", end='', flush=True)
        line = await reader.readline()
        if not line:
            return None
        content = line.decode().strip()
        if content:  # Skip empty lines
            return content

async def handle_ws_message(msg: aiohttp.WSMessage) -> None:
    """Handle incoming WebSocket messages."""
    try:
        data = json.loads(msg.data)
        method = data.get('method')
        params = data.get('params', {})
        
        if method == 'initialize':
            print("INIT", params)
        elif method == 'pub':
            print("PUB", params)
        else:
            print("*" * 80)
            print("ERROR, BAD PACKET", data)
            print("*" * 80)
    except json.JSONDecodeError:
        print(f"Failed to decode message: {msg.data}")
    except Exception as e:
        print(f"Error handling message: {e}")

async def chat_client():
    """Main chat client function using asyncio."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.ws_connect(WS_URL) as ws:
                print(f"Connected to {WS_URL}")
                
                # Queue for sending messages from input to WebSocket
                send_queue = asyncio.Queue()
                
                # Event to signal when we should exit
                done = asyncio.Event()
                
                async def handle_stdin():
                    """Handle user input and put messages in the send queue."""
                    while True:
                        try:
                            content = await read_stdin()
                            if content is None:  # EOF
                                break
                                
                            # Handle role specification
                            role = 'user'
                            if content.startswith('system: '):
                                role = 'system'
                                content = content[len('system: '):].strip()
                            
                            await send_queue.put((content, role))
                            
                        except asyncio.CancelledError:
                            break
                        except Exception as e:
                            print(f"\n[!] Input error: {e}")
                            break
                    
                    # Signal that we're done
                    done.set()
                
                async def handle_websocket():
                    """Handle incoming WebSocket messages."""
                    try:
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                await handle_ws_message(msg)
                            elif msg.type == aiohttp.WSMsgType.CLOSED:
                                print("\n[!] Connection closed by server")
                                break
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                print(f"\n[!] Connection error: {ws.exception()}")
                                break
                    except ConnectionResetError:
                        print("\n[!] Connection lost")
                    except Exception as e:
                        print(f"\n[!] WebSocket error: {e}")
                    finally:
                        # Signal that we're done
                        done.set()
                
                # Start both tasks
                input_task = asyncio.create_task(handle_stdin())
                ws_task = asyncio.create_task(handle_websocket())
                
                # Main loop - process messages from input to WebSocket
                while not done.is_set():
                    try:
                        # Wait for either a message to send or the done event
                        get_message = asyncio.create_task(send_queue.get())
                        done_wait = asyncio.create_task(done.wait())
                        
                        done_fut, pending = await asyncio.wait(
                            [get_message, done_wait],
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        
                        # Cancel the pending task
                        for task in pending:
                            task.cancel()
                        
                        # If we got a message to send
                        if get_message in done_fut and not get_message.cancelled():
                            content, role = await get_message
                            try:
                                await pub(ws, CH_IN, content, role=role)
                            except ConnectionResetError:
                                print("\n[!] Failed to send message - connection lost")
                                done.set()
                    
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        print(f"\n[!] Error: {e}")
                        break
                
                # Clean up
                input_task.cancel()
                ws_task.cancel()
                
                # Wait for tasks to finish
                await asyncio.gather(input_task, ws_task, return_exceptions=True)
                
        except Exception as e:
            print(f"\n[!] Connection error: {e}")
            return 1
    
    return 0

def main():
    """Entry point for the chat client."""
    try:
        return asyncio.run(chat_client())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
