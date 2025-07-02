#!/usr/bin/env python3
"""
Ollama Tool Calling Example
Based on official Ollama Python API examples
"""

import asyncio
import json
from ollama import AsyncClient

async def main():
    # Initialize the client
    client = AsyncClient()
    
    # Define the tool (function) that the model can call
    def calculator(expression: str) -> str:
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"Error: {e}"
    
    # Define the tool schema
    tools = [
        {
            "name": "calculator",
            "description": "Evaluate a mathematical expression",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "The mathematical expression to evaluate"}
                },
                "required": ["expression"]
            }
        }
    ]
    
    # Start the conversation
    messages = [
        {
            "role": "user",
            "content": "What is 123 * 456?"
        }
    ]
    
    print("Sending initial request...")
    
    # First request - should trigger tool use
    response = await client.chat(
        model="llama3.2",
        messages=messages,
        tools=tools,
        stream=False
    )
    
    # Check if tool was called
    if hasattr(response, 'message') and hasattr(response.message, 'tool_calls'):
        for tool_call in response.message.tool_calls:
            if tool_call.function.name == "calculator":
                # Parse arguments
                args = json.loads(tool_call.function.arguments)
                # Call the function
                result = calculator(**args)
                
                print(f"\nTool called with: {args}")
                print(f"Tool result: {result}")
                
                # Add the tool response
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
                print("\nGetting final response...")
                final_response = await client.chat(
                    model="llama3.2",
                    messages=messages,
                    stream=False
                )
                
                print("\nFinal response:")
                print(final_response.message.content)
                return
    
    # If we get here, no tool was called
    print("\nNo tool was called. Response:")
    print(response.message.content)

if __name__ == "__main__":
    asyncio.run(main())
