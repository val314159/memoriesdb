#!/usr/bin/env python3
"""
LLM Chat with Ollama and Tool Calling

Core functionality for interacting with Ollama LLM with tool calling support.
"""

import json
import inspect
import sys
from typing import Dict, List, Any, Callable, get_type_hints
import asyncio

# Import Ollama
try:
    from ollama import AsyncClient
    from rich.console import Console
    
    console = Console()
    
except ImportError as e:
    print(f"Error: {e}")
    print("Please install required packages with:")
    print("pip install ollama rich")
    sys.exit(1)

def calculator(expression: str) -> str:
    """Perform mathematical calculations
    
    Args:
        expression: The mathematical expression to evaluate
        
    Returns:
        The result of the calculation as a string
    """
    try:
        # Simple evaluation (in production, use a safer eval or a proper math parser)
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)  # Return just the result as string for easier parsing
    except Exception as e:
        return f"Error: {e}"

def get_tool_schema(func):
    """Generate tool schema from function docstring and annotations"""
    doc = inspect.getdoc(func) or ""
    params = inspect.signature(func).parameters
    hints = get_type_hints(func)
    
    # Parse docstring for parameter descriptions
    param_descs = {}
    current_param = None
    
    for line in doc.split('\n'):
        line = line.strip()
        if line.startswith('Args:'):
            continue
        if ':' in line and not line.startswith(' '):
            current_param, desc = line.split(':', 1)
            param_descs[current_param.strip()] = desc.strip()
        elif current_param and line:
            param_descs[current_param] += ' ' + line.strip()
    
    # Build schema
    properties = {}
    required = []
    
    for name, param in params.items():
        if name == 'self':
            continue
            
        param_type = hints.get(name, str)
        param_type_str = param_type.__name__ if hasattr(param_type, '__name__') else str
        
        # Map Python types to JSON schema types
        type_map = {
            'str': 'string',
            'int': 'integer',
            'float': 'number',
            'bool': 'boolean',
            'list': 'array',
            'dict': 'object'
        }
        
        properties[name] = {
            'type': type_map.get(param_type_str, 'string'),
            'description': param_descs.get(name, '')
        }
        
        # Check if parameter has a default value
        if param.default == inspect.Parameter.empty:
            required.append(name)
        else:
            properties[name]['default'] = param.default
    
    return {
        'name': func.__name__,
        'description': doc.split('\n')[0] if doc else '',
        'parameters': {
            'type': 'object',
            'properties': properties,
            'required': required
        },
        'function': func
    }

# Define available tools
TOOL_FUNCTIONS = [calculator]

# Generate tool schemas
AVAILABLE_TOOLS = {}
for func in TOOL_FUNCTIONS:
    tool = get_tool_schema(func)
    AVAILABLE_TOOLS[tool['name']] = tool

class LLMChat:
    def __init__(self, model: str = "llama3"):
        self.model = model
        self.client = AsyncClient()
        self.messages: List[Dict[str, str]] = []
        self.tools = list(AVAILABLE_TOOLS.values())
    
    async def chat_completion(self, prompt: str) -> str:
        """Send a chat message and get a response with detailed status messages"""
        console.print(f"\n[bold blue]Sending prompt to {self.model}:[/] {prompt}")
        self.messages.append({"role": "user", "content": prompt})
        
        try:
            # Prepare the request with tools
            console.print("[dim]Preparing request with tools...[/]")
            request = {
                "model": self.model,
                "messages": self.messages,
                "tools": [{
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                } for tool in AVAILABLE_TOOLS.values()]
            }
            console.print("[dim]Sending request to Ollama API...[/]")
            
            # Get the response
            console.print("[dim]Waiting for model response...[/]")
            try:
                response = await self.client.chat(**request)
                console.print("[green]✓ Got response from model[/]")
            except Exception as e:
                console.print(f"[red]Error from Ollama API: {str(e)}[/]")
                return f"Error: {str(e)}"
            
            # Handle tool calls if any
            if hasattr(response, 'tool_calls') and response.tool_calls:
                console.print("[yellow]Model requested tool usage:[/]")
                for i, tool_call in enumerate(response.tool_calls, 1):
                    console.print(f"  {i}. {tool_call.function.name}({tool_call.function.arguments})")
                tool_responses = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    if tool_name in AVAILABLE_TOOLS:
                        tool_func = AVAILABLE_TOOLS[tool_name]["function"]
                        # Convert arguments to correct types based on function signature
                        sig = inspect.signature(tool_func)
                        bound_args = sig.bind(**tool_args)
                        bound_args.apply_defaults()
                        console.print(f"[dim]Executing {tool_name} with args: {bound_args}")
                        try:
                            result = tool_func(*bound_args.args, **bound_args.kwargs)
                            console.print(f"[green]✓ {tool_name} result: {result}")
                            tool_responses.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": tool_name,
                                "content": str(result)
                            })
                        except Exception as e:
                            error_msg = f"Error in {tool_name}: {str(e)}"
                            console.print(f"[red]{error_msg}[/]")
                            return error_msg
                
                # Add tool responses to messages
                self.messages.extend([{"role": "assistant", "content": None, "tool_calls": response.tool_calls}])
                self.messages.extend(tool_responses)
                
                # Get final response after tool calls
                final_response = await self.chat_completion("")
                return final_response
            
            # Add assistant's response to messages
            self.messages.append({"role": "assistant", "content": response.message.content})
            return response.message.content
            
        except Exception as e:
            return f"Error: {str(e)}"
