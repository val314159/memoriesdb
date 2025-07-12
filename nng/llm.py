#!/usr/bin/env python3
'''
Let's assume we only have one convo at once!
and we'll use a JSON file!
whee!
'''
from gevent import monkey as _;_.patch_all()
import os, time, json, websocket, ollama
import funcs2 as funcs

from util import load_history_from_yml

messages = load_history_from_yml()
print('---')
for m in messages:
    print("MESSAGE:", m)
    pass
print('---')

filename = 'convo.jsonl'

def load_records():
    filename = 'convo.jsonl'
    pass

def save_record():
    pass



def recv(ws):
    raw = ws.recv()
    if not raw:
        raise EOFError
    return json.loads(raw)

def send(ws, msg):
    return ws.send( json.dumps(msg) )

def mesg(method, **params):
    return dict(method=method, params=params)

def pub(ws, channel, content='', **kw):
    return send(ws, mesg('pub',
                         channel = channel,
                         content = content, **kw))


NAME = os.getenv('NAME','llm')
IN_CHANNEL  = NAME+'-in'
OUT_CHANNEL = NAME+'-out'
WS_BASE = "ws://localhost:5002/ws"


class Convo:
    
    def __init__(_,tools=funcs.Tools, model='llama3.1'):
        _.tools, _.model, _.messages, _.ws = tools, model, [], None
        pass

    def connect_ws(_):
        '''we do it this way so error don't leave garbage in _.ws'''
        ws = websocket.WebSocket()
        ws.connect(f'{WS_BASE}?c={IN_CHANNEL}')
        _.ws = ws
        pass

    def send_output(_, content, role):
        #_id = insert_new_history(session_id, content, role=role)
        _.messages.append(dict(role=role, content=content))
        return pub(_.ws, OUT_CHANNEL, content, role=role, done=True)

    def append_user(_, content):
        #_id = insert_new_history(session_id, content, role='user')
        _.messages.append(dict(role='user',  content=content))
        pass

    def append_tool(_, name, arguments, output):
        print(">>>>>> APPEND TOOL")
        fn_dict = dict(name=name, arguments=arguments)
        tool_calls = [ dict(function=fn_dict) ]
        content =  json.dumps( tool_calls )
        #_id = insert_new_history( session_id,
        #                          content  =  json.dumps( tool_calls ),
        #                          role='tool', action="toolcall" )
        _.messages.append(  dict( role='tool', tool_calls=tool_calls )  )
        content = str(output)
        #_id = insert_new_history(session_id, content, role='tool', action="toolreturn")
        _.messages.append(dict(role='tool',
                               content=content,
                               name=name))
        pass

    def chat(_) -> ollama.ChatResponse:
        return ollama.chat(_.model,
                           messages=_.messages,
                           tools=_.tools,
                           #stream=True,
                           #format='json',
                           )

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
            #assert(not message.content and     message.tool_calls)
            if message.content:
                print("THIS IS WIERD, SHOULD THIS BE HAPPENING?")
                print("THERE ARE TOOL CALLS (w/ content)")
            else:
                print("THERE ARE TOOL CALLS (no content)")
                pass
            assert( len(message.tool_calls) == 1 )
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
        #print(ConnectionError)
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

    def load_session(_, user_id, session_id):
        _.history = []
        #_.history = load_full_session(user_id, session_id)
        messages = []
        for message in _.history:
            d1 = row2dict(message)
            if d1['_type'] == 'model':
                print("RESET THE MODEL", d1)
                if not _.model:
                    _.model = d1['content']
                    print("SET THE MODEL", _.model)
                    pass
                continue
            role    = d1['_role']
            content = d1['content']
            d2 = dict(role    = role,
                      content = content)
            messages.insert(0, d2)
            pass
        _.messages = messages
        print("MODEL", _.model)
        pass

    def main(_, _user_id=None,
             _session_id=None):
        _   .user_id  =    _user_id or    user_id
        _.session_id  = _session_id or session_id
        _.load_session(user_id, session_id)
        print("-------")
        for message in _.messages:
            print(3, message)
            pass
        print("-------")
        _.connect_ws()
        while 1:
            _.once()
            time.sleep(0.2)
            pass
        return print("EOF")
    pass

if __name__=='__main__':
    #init()

    user_id = None
    #user_id = get_user_id()
    #print("user_id", user_id)

    session_id = None
    #session_id = get_latest_session(user_id)
    #print("session_id", session_id)

    Convo().main()
