#!/usr/bin/env python3
"""Working Tool Chat

A minimal implementation that works with Ollama's API.
"""

import asyncio
import json
from ollama import AsyncClient

async def main():
    client = AsyncClient()
    
    # Simple calculator function
    def calculator(expression: str) -> str:
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"Error: {e}"
    
    # Tool definition
    tools = [
        {
            "name": "calculator",
            "description": "Evaluate a mathematical expression",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                },
                "required": ["expression"]
            }
        }
    ]
    
    # Start chat
    print("Chat started. Type 'exit' to quit.")
    messages = []
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit':
            break
            
        messages.append({"role": "user", "content": user_input})
        
        try:
            # Get initial response
            response = await client.chat(
                model="llama3.2:1b",
                messages=messages,
                tools=tools,
                stream=False
            )
            
            # Check if tool was called
            if hasattr(response, 'message') and hasattr(response.message, 'tool_calls'):
                tool_call = response.message.tool_calls[0]
                if tool_call.function.name == "calculator":
                    # Get arguments
                    args = json.loads(tool_call.function.arguments)
                    # Calculate result
                    result = calculator(args["expression"])
                    
                    # Add tool response
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": "calculator",
                                "arguments": tool_call.function.arguments
                            }
                        }]
                    })
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": "calculator",
                        "content": result
                    })
                    
                    # Get final response
                    final_response = await client.chat(
                        model="llama3.2:1b",
                        messages=messages,
                        stream=False
                    )
                    print(f"\nAssistant: {final_response.message.content}")
                    messages.append({"role": "assistant", "content": final_response.message.content})
                    continue
            
            # If no tool was called
            print(f"\nAssistant: {response.message.content}")
            messages.append({"role": "assistant", "content": response.message.content})
            
        except Exception as e:
            print(f"\nError: {str(e)}")
            # Fallback to direct response on error
            try:
                response = await client.chat(
                    model="llama3.2:1b",
                    messages=messages,
                    stream=False
                )
                print(f"\nAssistant: {response.message.content}")
                messages.append({"role": "assistant", "content": response.message.content})
            except:
                print("\nSorry, I encountered an error. Please try again.")

if __name__ == "__main__":
    asyncio.run(main())
