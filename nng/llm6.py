#!/usr/bin/env python3
'''
Let's assume we only have one convo at once!
and we'll use a JSON file!
whee!
'''
from gevent import monkey as _;_.patch_all()
import os, sys, time, json, websocket, ollama
import funcs2 as funcs

#from util import load_history_from_yml, fork_history_to_yml
#from util import load_history_from_txt
#from util import start_history_to_yml


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
        _.tools, _.model, _.ws = tools, model, None
        pass

    def connect_ws(_):
        '''we do it this way so error don't leave garbage in _.ws'''
        ws = websocket.WebSocket()
        ws.connect(f'{WS_BASE}?c={IN_CHANNEL}')
        _.ws = ws
        pass

    def insert_history(_, uuid, session_id, content, role='user', **kw): 
        muid = create_memory(session_id=session_id,
                             user_id=uuid,
                             content=content,
                             role=role,
                             kind='history',
                             **kw)
        euid = create_memory_edge(muid, session_id, 'belongs_to')
        pass

    def send_output(_, uuid, session_id, content, role, done):
        _id = insert_history(uuid, session_id, content, role=role, done=done)
        return pub(_.ws, OUT_CHANNEL, content, role=role, done=done)

    def append_user(_, uuid, session_id, content):
        _id = insert_history(uuid, session_id, content, role='user')
        pass

    def append_tool(_, uuid, session_id, name, arguments, output):
        print(">>>>>> APPEND TOOL", (name, arguments, output))
        fn_dict = dict(name=name, arguments=arguments)
        tool_calls = [ dict(function=fn_dict) ]
        content =  json.dumps( tool_calls )
        _id = insert_history(uuid, session_id, '', role='assistant', tool_calls=tool_calls)
        content = str(output)
        d = dict(role='assistant', content=content, name=name)
        _id = insert_history(uuid, session_id, content, role='assistant', name=name)
        pass

    def materialize_history(_, uuid, session_id):
        ret = []
        for msg in db.load_simplified_convo(session_id):
            ret.append(msg)
            pass
        return ret

    def chat(_, uuid, session_id) -> ollama.ChatResponse:
        retries = -1
        messages = _.materialize_history(uuid, session_id)
        while 1:
            retries += 1
            if retries > 3:
                print("TOO MANY RETRIES")
                exit(1)
            return ollama.chat(model=_.model, messages=messages,
                               tools=_.tools, stream=True, format='json')

    def process_tool_response_message(_, uuid, session_id, message, done = None):
        if not message:
            print("4 NO MESSAGE")
            raise exit(1)
        elif     message.content and not message.tool_calls:
            print("5 RESPOND TO USER - THERE IS CONTENT RETURNED FROM TOOLCALL")
            _.send_output(uuid, session_id, message.content, message.role, done)
        elif not message.content and     message.tool_calls:
            print("6 THERE ARE TOOL CALLSZZZ")
            raise Exception('too deep')
        else:
            if not done:
                raise Exception('wtf')
            _.send_output(uuid, session_id, message.content, message.role, done)
        pass

    def perform_tool_call(_, uuid, session_id, name, arguments, done):
        print("THERE IS A TOOL CALL (no content)")
        if name == 'respond_to_user':
            # DON'T call a function here, we'll just handle it right here ourselves
            role = 'assistant'
            content = arguments['message']
            print(">> RESPOND TO USER (VIA TOOL) <<", content)
            _.send_output(uuid, session_id, content, role, done)
        elif function_to_call := getattr(funcs, name, ''):
            print(">> EVAL FUNC TOOL CALL <<")
            print('Calling function:', name)
            print('Arguments:', arguments)
            output = function_to_call(**arguments)
            print('Function output:', output)
            _.append_tool(uuid, session_id, name, arguments, output)
            print('Tell ollama about output; messages = ', _.messages)
            print("2 Waiting on ollama.chat()...")
            response = _.chat(uuid, session_id)
            print(1,type(response))
            print(2,type(response))
            print(type(response))
            print(type(response))
            if not response:
                print("0 NO RESPONSE")
                raise exit(7)
            print("33 RESPONSE", response)
            for message in response:
                print("MMM", message)
                xx = _.process_tool_response_message(uuid, session_id,
                                                     message.message, message.done)
                print("XXX", (xx,))
            else:
                pass
        else:
            print('Function', name, 'not found')
            raise exit(1)
        pass

    def process_message(_, uuid, session_id, message, done=None):
        if not message:
            print("NO MESSAGE")
            raise exit(1)
        if message.get('content') is None and not message.tool_calls:
            print("THIS NO CONTENT AND NO TOOL CALLS (maybe an image?)")
            raise exit(5)
        if     message.content and not message.tool_calls:
            print("THERE IS CONTENT ONLY")
            print(">> RESPOND TO USER (DIRECTLY) <<", message.role, message.content)
            _.send_output(uuid, session_id, message.content, message.role, done)
            ### elif not message.content and     message.tool_calls:
        elif   message.content=='' and not message.tool_calls:
            print("THERE IS CONTENT ONLY (BUT ITS BLANK)")
            print(">> RESPOND TO USER (DIRECTLY) <<", message.role, message.content)
            _.send_output(uuid, session_id, message.content, message.role, done)
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
            print("TOOL CA", message.tool_calls)
            tool_call = message.tool_calls[0].function
            print("TOOL CALL", tool_call)
            _.perform_tool_call(uuid, session_id, tool_call.name, tool_call.arguments, done)
            pass
        pass



    
    def got_init(_, params):
        print("INIT", params)
        pass

    def got_pub(_, params):
        print("GOT PUB YYYYYY", params)
        uuid = params.get('uuid')
        session_id = params['session']
        content = params['content']

        # lets save it to the DB here
        _.append_user(uuid, session_id, content)
        
        print("_.messages =", json.dumps(_.messages))
        print("Waiting on ollama.chat()...")
        response = _.chat()
        if not response:
            print("NO RESPONSE")
            raise exit(1)
        print("PUBB..RESPONSE", type(response))
        if str(type(response)) == "<class 'generator'>":
            print("=========1")
            for message in response:
                print("==")
                done = message.done
                mesg = message.message
                print("M..", message)
                print("M.M", done, mesg)
                _.process_message(mesg, done)
                pass
            print("=========")
            return
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
            _.got_pub(params)
            #_.got_pub(params['content'])
        else:
            print("*"*80)
            print("ERROR, BAD PACKET", msg)
            print("*"*80)
            pass
        pass

    def main(_):
        _.connect_ws()
        while 1:
            _.once()
            time.sleep(0.2)
            pass
        return print("EOF")

    pass

if __name__=='__main__':
    Convo().main()
