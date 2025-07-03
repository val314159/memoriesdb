#!/usr/bin/env python3
"""
Database-enabled async chat client for MemoriesDB

This chat client:
1. Uses the system user (00000000-0000-0000-0000-000000000000)
2. Saves all sent and received messages to the database
3. Maintains conversation history
"""

import asyncio
import json
import os
import sys
import time
import uuid
import aiohttp
from typing import Optional, Dict, Any, Tuple
from db_utils import get_pool, set_current_user_id, execute, query_fetchone

# Environment variables
CH = os.getenv('CH', 'llm')
CH_IN = os.getenv('CH_IN', f'{CH}-in')
CH_OUT = os.getenv('CH_OUT', f'{CH}-out')
CHANNELS = [CH_OUT]
WS_BASE = "ws://localhost:5002/ws"
WS_ARGS = '?c=' + '&c='.join(CHANNELS)
WS_URL = f"{WS_BASE}{WS_ARGS}"

# System user ID for database operations
SYSTEM_USER_ID = '00000000-0000-0000-0000-000000000000'

def mesg(method: str, **params) -> Dict[str, Any]:
    """Create a message dictionary with method and parameters."""
    return {"method": method, "params": params}

async def save_message(content: str, role: str, direction: str, metadata: Optional[Dict] = None) -> str:
    """Save a message to the database.
    
    Args:
        content: The message content
        role: 'user', 'system', or 'assistant'
        direction: 'incoming' or 'outgoing'
        metadata: Additional metadata to store
        
    Returns:
        The ID of the saved message
    """
    # Note: User ID is set once at startup in chat_client()
    # Prepare metadata
    msg_metadata = {
        'role': role,
        'direction': direction,
        'timestamp': time.time(),
        **(metadata or {})
    }
    
    # Insert the message into the database
    result = await execute(
        """
        INSERT INTO memories (kind, content, created_by, _metadata)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        """,
        ('chat_message', content, SYSTEM_USER_ID, json.dumps(msg_metadata))
    )
    
    if result and len(result) > 0:
        return result[0][0]
    return None

async def read_stdin() -> Optional[str]:
    """Read a line from stdin asynchronously."""
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    
    print("user> ", end='', flush=True)
    line = await reader.readline()
    if not line:
        return None
    return line.decode().strip()

async def handle_ws_message(msg: aiohttp.WSMessage) -> None:
    """Handle incoming WebSocket messages."""
    try:
        data = json.loads(msg.data)
        method = data.get('method')
        params = data.get('params', {})
        
        if method == 'initialize':
            print("INIT", params)
        elif method == 'pub':
            # Save incoming messages to the database
            content = params.get('content', '')
            role = params.get('role', 'assistant')
            
            # Only save non-empty messages
            if content.strip():
                await save_message(
                    content=content,
                    role=role,
                    direction='incoming',
                    metadata={'channel': params.get('channel')}
                )
                
            # Print the message
            prefix = f"{role.upper()}: " if role != 'user' else ""
            print(f"\n{prefix}{content}")
            print("\nuser> ", end='', flush=True)
            
    except json.JSONDecodeError:
        print("\n[!] Failed to decode message")
    except Exception as e:
        print(f"\n[!] Error handling message: {e}")

async def chat_client():
    """Main chat client function using asyncio."""
    # Initialize database connection pool
    await get_pool()
    
    # Set the system user for all database operations in this process
    # This only needs to be done once as it sets a module-level variable
    set_current_user_id(SYSTEM_USER_ID)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.ws_connect(WS_URL) as ws:
                print(f"Connected to {WS_URL}")
                print("Type your message and press Enter. Start with 'system: ' for system messages.")
                
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
                            
                            # Save the outgoing message to the database
                            message_id = await save_message(
                                content=content,
                                role=role,
                                direction='outgoing',
                                metadata={'channel': CH_IN}
                            )
                            
                            if message_id:
                                await send_queue.put((content, role, message_id))
                            else:
                                print("\n[!] Failed to save message to database")
                            
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
                            content, role, message_id = await get_message
                            try:
                                # Send the message
                                message = mesg('pub', channel=CH_IN, content=content, role=role)
                                await ws.send_str(json.dumps(message))
                                
                                # Update the message with sent status
                                await execute(
                                    """
                                    UPDATE memories 
                                    SET _metadata = _metadata || %s::jsonb
                                    WHERE id = %s
                                    """,
                                    (json.dumps({'sent_at': time.time()}), message_id)
                                )
                                
                            except ConnectionResetError:
                                print("\n[!] Failed to send message - connection lost")
                                await execute(
                                    """
                                    UPDATE memories 
                                    SET _metadata = _metadata || %s::jsonb
                                    WHERE id = %s
                                    """,
                                    (json.dumps({'error': 'failed_to_send', 'timestamp': time.time()}), message_id)
                                )
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
