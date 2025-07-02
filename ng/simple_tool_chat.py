#!/usr/bin/env python3
"""Simple Chat with Tool Calling

Basic implementation with direct tool calling support following Ollama's patterns.
"""

import asyncio
import json
from typing import Dict, List, Any
from ollama import AsyncClient

# Simple calculator function
def calculator(expression: str) -> str:
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"

# Tool definition following Ollama's format
TOOLS = [
    {
        "name": "calculator",
        "description": "Evaluate a mathematical expression",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression to evaluate"}
            },
            "required": ["expression"]
        }
    }
]

class ToolChat:
    def __init__(self, model: str = "llama3.2:1b"):
        self.model = model
        self.client = AsyncClient()
        self.messages: List[Dict[str, Any]] = []
    
    async def chat(self, message: str) -> str:
        # Add user message
        self.messages.append({"role": "user", "content": message})
        
        # Initial request
        request = {
            "model": self.model,
            "messages": self.messages,
            "stream": False,
            "tools": TOOLS
        }
        
        while True:
            # Get response from Ollama
            response = await self.client.chat(**request)
            
            # Check if response contains tool calls
            if hasattr(response, 'message') and hasattr(response.message, 'tool_calls'):
                for tool_call in response.message.tool_calls:
                    if tool_call.function.name == "calculator":
                        # Extract arguments
                        args = json.loads(tool_call.function.arguments)
                        # Call the calculator function
                        result = calculator(**args)
                        
                        # Add the tool response
                        self.messages.append({
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
                        
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": "calculator",
                            "content": result
                        })
                        
                        # Update request for next iteration
                        request["messages"] = self.messages
                        continue
            
            # If we get here, we have a final response
            final_response = response.message.content
            self.messages.append({"role": "assistant", "content": final_response})
            return final_response

async def main():
    chat = ToolChat()
    print("Simple Tool Chat - Type 'exit' to quit")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit':
            break
            
        response = await chat.chat(user_input)
        print(f"\nAssistant: {response}")

if __name__ == "__main__":
    asyncio.run(main())
