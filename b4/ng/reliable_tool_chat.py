#!/usr/bin/env python3
"""Reliable Tool Calling Chat

A simplified implementation that works with Ollama's API.
"""

import asyncio
import json
from ollama import AsyncClient

class ToolChat:
    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model
        self.client = AsyncClient()
        self.messages = []
        
        # Define the calculator tool
        self.tools = [
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
    
    async def calculate(self, expression: str) -> str:
        """Simple calculator function"""
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"Error: {e}"
    
    async def chat_loop(self):
        """Main chat loop"""
        print("Chat started. Type 'exit' to quit.")
        
        while True:
            user_input = input("\nYou: ")
            if user_input.lower() == 'exit':
                break
                
            self.messages.append({"role": "user", "content": user_input})

            print("model", self.model, self.messages)
            try:
                # Get initial response
                response = await self.client.chat(
                    model=self.model,
                    messages=self.messages,
                    tools=self.tools,
                    stream=False
                )
                print("INIT RTESP", response)
                # Check if tool was called
                if hasattr(response, 'message') and hasattr(response.message, 'tool_calls'):
                    for tool_call in response.message.tool_calls:
                        if tool_call.function.name == "calculator":
                            # Get arguments
                            args = json.loads(tool_call.function.arguments)
                            # Calculate result
                            result = await self.calculate(args["expression"])
                            
                            # Add tool response
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
                            
                            # Get final response
                            final_response = await self.client.chat(
                                model=self.model,
                                messages=self.messages,
                                stream=False
                            )
                            print(f"\nAssistant: {final_response.message.content}")
                            self.messages.append({"role": "assistant", "content": final_response.message.content})
                            continue
                
                # If no tool was called
                print(f"\nAssistant: {response.message.content}")
                self.messages.append({"role": "assistant", "content": response.message.content})
                
            except Exception as e:
                print(f"\nError: {str(e)}")

async def main():
    chat = ToolChat()
    await chat.chat_loop()

if __name__ == "__main__":
    asyncio.run(main())
