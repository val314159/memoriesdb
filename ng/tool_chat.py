#!/usr/bin/env python3
"""Simple LLM Chat with Ollama

A minimal implementation for fast chat responses.
"""

import asyncio
from typing import List, Dict
from ollama import AsyncClient

class SimpleChat:
    def __init__(self, model: str = "llama3"):
        self.model = model
        self.client = AsyncClient()
        self.messages: List[Dict[str, str]] = []
    
    async def chat(self, message: str) -> str:
        """Send a message and get a response"""
        self.messages.append({"role": "user", "content": message})
        
        response = await self.client.chat(
            model=self.model,
            messages=self.messages,
            options={"temperature": 0.1}
        )
        
        response_text = response['message']['content']
        self.messages.append({"role": "assistant", "content": response_text})
        return response_text

async def main():
    chat = SimpleChat(model="llama3")
    print("Simple Chat - Type 'exit' to quit")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit':
            break
            
        response = await chat.chat(user_input)
        print(f"\nAssistant: {response}")

if __name__ == "__main__":
    asyncio.run(main())
