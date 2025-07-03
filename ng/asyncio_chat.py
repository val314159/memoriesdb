#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import aiohttp
import uuid
from db_utils import create_memory, set_current_user_id, get_pool, execute

CH = os.getenv('CH', 'llm')
CH_IN = os.getenv('CH_IN', f'{CH}-in')
CH_OUT = os.getenv('CH_OUT', f'{CH}-out')
CHANNELS = [CH_OUT]
WS_BASE = "ws://localhost:5002/ws"
WS_ARGS = '?c=' + '&c='.join(CHANNELS)
WS_URL = f"{WS_BASE}{WS_ARGS}"

def mesg(method, **params):
    return {"method": method, "params": params}

async def send(ws, msg):
    await ws.send_str(json.dumps(msg))

async def pub(ws, channel, content='', **kw):
    # Save the message to memories if it's a user or system message
    role = kw.get('role', 'user')
    if role in ['user', 'system']:
        try:
            # Use a default user ID for now, or get it from environment/config
            user_id = os.getenv('USER_ID', '00000000-0000-0000-0000-000000000000')
            set_current_user_id(user_id)  # Set user context for db operations
            memory_content = f"{role.upper()}: {content}"
            
            # Set the current user ID which will be used by the trigger
            set_current_user_id(user_id)
            
            # Create memory using db_utils execute function
            try:
                result = await execute(
                    """
                    INSERT INTO memories (kind, content, created_by, _metadata)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                    """,
                    ('chat_message', memory_content, user_id, json.dumps({"role": role}))
                )
                
                # The execute function now returns the result of the RETURNING clause
                if result and len(result) > 0 and result[0]:
                    memory_id = result[0][0]
                    print(f"\n[Saved to memories as {memory_id}]")
                else:
                    # If we get here, the INSERT worked but we didn't get an ID back
                    print("\n[Warning: Memory saved but no ID returned - this shouldn't happen with RETURNING id]")
                    
            except Exception as e:
                print(f"\n[Error saving to memories: {e}]")
        except Exception as e:
            print(f"\n[Error saving to memories: {e}")
    
    # Send the message through WebSocket
    await send(ws, mesg('pub', channel=channel, content=content, **kw))

async def read_stdin():
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    
    while True:
        print("user> ", end='', flush=True)
        line = await reader.readline()
        if not line:
            break
        content = line.decode().strip()
        if content:  # Skip empty lines
            return content
    return None

async def handle_ws_message(msg):
    try:
        data = json.loads(msg.data)
        method = data.get('method')
        params = data.get('params', {})
        
        if method == 'initialize':
            print("INIT", params)
        elif method == 'pub':
            print(f"PUB {params}")
        else:
            print("*" * 80)
            print("ERROR, BAD PACKET", data)
            print("*" * 80)
    except json.JSONDecodeError:
        print(f"Failed to decode message: {msg.data}")
    except Exception as e:
        print(f"Error handling message: {e}")

async def ensure_default_user():
    """Return the system user ID (zero UUID).
    The system user is created in the database schema initialization."""
    return '00000000-0000-0000-0000-000000000000'

async def chat_client():
    # Initialize the database connection pool
    await get_pool()  # This will initialize the connection pool
    
    # Ensure default user exists
    default_user_id = await ensure_default_user()
    if not default_user_id:
        print("Warning: Could not ensure default user exists. Messages may not be saved.")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.ws_connect(WS_URL) as ws:
                print(f"Connected to {WS_URL}")
                
                # Start a task to handle incoming messages
                async def listen_for_messages():
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await handle_ws_message(msg)
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            print("WebSocket connection closed")
                            break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            print(f"WebSocket error: {ws.exception()}")
                            break
                
                listener = asyncio.create_task(listen_for_messages())
                
                # Main loop for user input
                try:
                    while True:
                        content = await read_stdin()
                        if content is None:
                            break
                            
                        role = 'user'
                        if content.startswith('system: '):
                            role = 'system'
                            content = content[len('system: '):]
                        
                        await pub(ws, CH_IN, content, role=role)
                except asyncio.CancelledError:
                    pass
                finally:
                    listener.cancel()
                    await listener
        except Exception as e:
            print(f"Connection error: {e}")
            return 1
    return 0

def main():
    try:
        asyncio.run(chat_client())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
