#!/usr/bin/env python3
from wsutil import *
import json
import ollama
import funcs2 as funcs
NAME = os.getenv('NAME','llm')
IN_CHANNEL  = NAME+'-in'
OUT_CHANNEL = NAME+'-out'
WS_BASE = "ws://localhost:5002/ws"
class Chat:
  def __init__(_,tools=funcs.Tools):
    _.ws = None
    _.tools = tools
    _.messages = [dict(role='system',
                       content=
                       " You are a chatty, friendly AI assistant named Ava."
                       " If you can't find a good tool,"
                       " just output what you would say to respond_to_user.")]
    pass
  def connect(_):
    '''we do it this way so error don't leave garbage in _.ws'''
    import websocket
    ws = WebSocket()
    ws.connect(f'{WS_BASE}?c={IN_CHANNEL}')
    _.ws = ws
    pass
  def append_user(_, user_input):
    _.messages.append(dict(role='user',      content=user_input))
    pass
  def append_tool(_, name, arguments, output):
    _.messages.append(dict(role='tool',
                           tool_calls=[dict(
                             function=dict(
                               name=name,
                               arguments=arguments,
                             ))]))
    _.messages.append(dict(role='tool',
                           content=str(output),
                           name=name))
    pass
  def chat(_) -> ollama.ChatResponse:
    return ollama.chat('llama3.1',
                       messages=_.messages,
                       tools=_.tools,
                       #stream=True,
                       #format='json',
                       )
  def send_output(_, content, role):
    # send output to Ava      
    _.messages.append(dict(role=role, content=content))
    return pub(_.ws, OUT_CHANNEL, content, role=role, done=True)
  def process_tool_response_message(_, message):
    if not message:
      print("4 NO MESSAGE")
      raise exit(1)
    elif     message.content and not message.tool_calls:
      print("5 RESPOND TO USER - THERE IS CONTENT RETURNED FROM TOOLCALL")
      _.send_output(message.content, message.role)
    elif not message.content and     message.tool_calls:
      print("6 THERE ARE TOOL CALLSZZZ")
      raise Exception('too deep')
    else:
      raise Exception('wtf')
    pass
  def perform_tool_call(_, name, arguments):
    print("THERE IS A TOOL CALL (no content)")
    if name == 'respond_to_user':
      # DON'T call a function here, we'll just handle it right here ourselves
      role = 'assistant'
      content = arguments['message']
      print(">> RESPOND TO USER (VIA TOOL) <<", content)
      _.send_output(content, role)
    elif function_to_call := getattr(funcs, name, ''):
      print(">> EVAL FUNC TOOL CALL <<")
      print('Calling function:', name)
      print('Arguments:', arguments)
      output = function_to_call(**arguments)
      print('Function output:', output)
      _.append_tool(name, arguments, output)
      print('Tell ollama about output; messages = ', _.messages)
      print("2 Waiting on ollama.chat()...")
      response = _.chat()
      if not response:
        print("0 NO RESPONSE")
        raise exit(7)
      print("3 RESPONSE", response)
      return _.process_tool_response_message(response.message)
    else:
      print('Function', name, 'not found')
      raise exit(1)
    pass
  def process_message(_, message):
    if not message:
      print("NO MESSAGE")
      raise exit(1)
    if not message.content and not message.tool_calls:
      print("THIS NO CONTENT AND NO TOOL CALLS (maybe an image?)")
      raise exit(5)
    if     message.content and not message.tool_calls:
      print("THERE IS CONTENT ONLY")
      print(">> RESPOND TO USER (DIRECTLY) <<", message.role, message.content)
      _.send_output(message.content, message.role)
    ### elif not message.content and     message.tool_calls:
    else:
      assert(not message.content and     message.tool_calls)
      print("THERE ARE TOOL CALLS (no content)")
      assert( len(message.tool_calls) == 1)
      tool_call = message.tool_calls[0].function
      _.perform_tool_call(tool_call.name, tool_call.arguments)
      pass
    pass
  def got_init(_, params):
    print("INIT", params)
    pass
  def got_pub(_, user_input):
    print("GOT PUB YYYYYY", user_input)
    _.append_user(user_input)
    print("_.messages =", json.dumps(_.messages))
    print("Waiting on ollama.chat()...")
    response = _.chat()
    if not response:
      print("NO RESPONSE")
      raise exit(1)
    print("RESPONSE", response)
    return _.process_message(response.message)
  def once(_):
    print("Waiting on socket...")
    msg = recv(_.ws)
    print("Got", (msg,), "!")
    method = msg.get('method')
    params = msg.get('params',{})
    if method=='initialize':
      _.got_init(params)
    elif method=='pub':
      _.got_pub(params['content'])
    else:
      print("*"*80)
      print("ERROR, BAD PACKET", msg)
      print("*"*80)
      pass
    pass
  def main(_):
    _.connect()
    while 1:
      _.once()
      time.sleep(0.2)
      pass
    return print("EOF")
  pass
if __name__=='__main__':
  Chat().main()
