import asyncio
import aiohttp
import json
import os
from datetime import datetime as dt
from colorama import Fore, Style, init

model = "llama3.1"  # Global model variable

async def ainput(prompt): 
    return await asyncio.get_event_loop().run_in_executor(None, input, prompt)

class Logger:
    def __init__(self, file="chat.jsonl"):
        self.file = file
        self.session = dt.now().isoformat()
    
    def write(self, data):
        with open(self.file, "a") as f:
            f.write(json.dumps(data) + "\n")
    
    def new_session(self, model, name=None):
        self.session = name or dt.now().isoformat()
        self.write({"type": "start", "session": self.session, "model": model})
    
    def log_message(self, role, content):
        self.write({"role": role, "content": content})
    
    def log_model_change(self, model):
        self.write({"type": "model", "model": model})
    
    def load_session(self, name):
        if not os.path.exists(self.file):
            return [], "llama3.1"
        
        messages = []
        model = "llama3.1"
        in_session = False
        
        for line in open(self.file):
            data = json.loads(line)
            
            if data.get("session") == name:
                in_session = True
                model = data.get("model", model)
            elif data.get("type") == "start":
                in_session = data["session"] == name
                model = data.get("model", model)
            elif in_session:
                if data.get("type") == "model":
                    model = data["model"]
                elif "role" in data:
                    messages.append({"role": data["role"], "content": data["content"]})
        
        self.session = name
        return messages, model
    
    def list_sessions(self):
        if not os.path.exists(self.file):
            return set()
        
        sessions = set()
        for line in open(self.file):
            data = json.loads(line)
            if "session" in data:
                sessions.add(data["session"])
        return sessions

async def chat_with_model(messages):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:11434/api/chat",
            json={"model": model, "messages": messages, "stream": False}
        ) as response:
            result = await response.json()
            return result.get("message", {}).get("content", f"Error: {result}")

async def main():
    global model
    init()  # Initialize colorama
    logger = Logger()
    messages = []
    
    print(f"{Fore.CYAN}Chat - /n[ew] [name] /o[ld] <n> /l[ist] /m[odel] <n> /c[lear] /s[ystem] <msg>{Style.RESET_ALL}")
    
    while True:
        try:
            user_input = await ainput("› ")
            
            if user_input.startswith("/n"):
                name = user_input[2:].strip() or None
                if name and name in logger.list_sessions():
                    print(f"{Fore.RED}Session '{name}' already exists{Style.RESET_ALL}")
                    continue
                messages = []
                logger.new_session(model, name)
                print(f"{Fore.GREEN}New session: {logger.session}{Style.RESET_ALL}")
            
            elif user_input.startswith("/o "):
                name = user_input[3:]
                messages, model = logger.load_session(name)
                print(f"{Fore.GREEN}Loaded {name}: {len(messages)} messages{Style.RESET_ALL}")
            
            elif "/list".startswith(user_input) and len(user_input) >= 2:
                sessions = sorted(logger.list_sessions())
                print(f"{Fore.CYAN}Sessions: {sessions}{Style.RESET_ALL}")
            
            elif user_input.startswith("/m "):
                model = user_input[3:]
                logger.log_model_change(model)
                print(f"{Fore.MAGENTA}Model: {model}{Style.RESET_ALL}")
            
            elif "/clear".startswith(user_input) and len(user_input) >= 2:
                messages = []
                print(f"{Fore.YELLOW}Messages cleared{Style.RESET_ALL}")
            
            elif user_input.startswith("/s "):
                sys_message = user_input[3:]
                messages.append({"role": "system", "content": sys_message})
                logger.log_message("system", sys_message)
                print(f"{Fore.YELLOW}System: {sys_message}{Style.RESET_ALL}")
            
            elif user_input:
                messages.append({"role": "user", "content": user_input})
                logger.log_message("user", user_input)
                
                response = await chat_with_model(messages)
                messages.append({"role": "assistant", "content": response})
                logger.log_message("assistant", response)
                
                print(f"{Fore.BLUE}Bot: {response}{Style.RESET_ALL}")
        
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    asyncio.run(main())
