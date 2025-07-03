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
    connection_lost = asyncio.Event()
    
    async def handle_connection():
        async with aiohttp.ClientSession() as session:
            try:
                async with session.ws_connect(WS_URL) as ws:
                    print(f"Connected to {WS_URL}")
                    
                    # Start a task to handle incoming messages
                    async def listen_for_messages():
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
                            print(f"\n[!] Unexpected error: {e}")
                        finally:
                            connection_lost.set()
                            if not ws.closed:
                                await ws.close()
                    
                    # Start the message listener
                    listener = asyncio.create_task(listen_for_messages())
                    
                    # Main input loop
                    while not connection_lost.is_set():
                        # Use asyncio.wait_for to periodically check connection status
                        try:
                            content = await asyncio.wait_for(read_stdin(), timeout=0.5)
                            if content is None:  # EOF
                                break
                                
                            # Handle role specification
                            role = 'user'
                            if content.startswith('system: '):
                                role = 'system'
                                content = content[len('system: '):].strip()
                            
                            # Send the message
                            try:
                                await pub(ws, CH_IN, content, role=role)
                            except ConnectionResetError:
                                print("\n[!] Failed to send message - connection lost")
                                break
                                
                        except asyncio.TimeoutError:
                            # Check if connection was lost while waiting for input
                            if connection_lost.is_set():
                                break
                            continue
                        except asyncio.CancelledError:
                            break
                        
                    # Clean up listener task
                    if not listener.done():
                        listener.cancel()
                        try:
                            await listener
                        except:
                            pass
                            
            except Exception as e:
                print(f"\n[!] Connection error: {e}")
                connection_lost.set()
    
    # Run the connection handler
    connection_task = asyncio.create_task(handle_connection())
    
    try:
        await connection_task
    except asyncio.CancelledError:
        pass
    finally:
        # Ensure we clean up if still connected
        if not connection_lost.is_set():
            connection_lost.set()
        if not connection_task.done():
            connection_task.cancel()
            try:
                await connection_task
            except:
                pass
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
