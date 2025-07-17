from typing import Any, Dict, List, Optional, Union, cast
import os, time, json, websocket, ollama
import db_sync as db
from logging_setup import get_logger
import traceback


logger = get_logger(__name__)


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
    ws.send(channel)
    return send(ws, mesg('pub',
                         channel = channel,
                         content = content, **kw))


NAME = os.getenv('NAME','llm')
IN_CHANNEL  = NAME+'-in'
OUT_CHANNEL = NAME+'-out'
WS_BASE = "ws://localhost:5002/ws"


class EphemeralSessionProxy:

    def error_output(_):
        output = traceback.format_exc()
        print("\\ERROR", '*'*40)
        print(output)
        print( "/ERROR", '*'*40)
        return output
                
    def __init__(_, uuid, session_id, funcs,
                 ws, model, tools, out_channel):
        _.uuid, _.session_id, _.funcs = uuid, session_id, funcs
        _.ws, _.model, _.tools      = ws, model, tools
        _.out_channel = out_channel
        pass

    def materialize_history(_):
        """
        this thin wrapper will grow into its own subststem
        """
        ret = []
        for msg in db.load_simplified_convo(_.session_id):
            ret.append(msg)
            pass
        return ret

    def pub_content(_, role, content='', **kw):
        pub(_.ws, _.out_channel, content, role=role, **kw)

    def append_hist(_, role, content='', **kw):
        content = str(content)
        muid = db.create_memory(session_id=_.session_id,
                                user_id=_.uuid,
                                content=content,
                                role=role,
                                kind='history',
                                **kw)
        euid = db.create_memory_edge(muid, _.session_id, 'belongs_to')
        _.pub_content(role, content, **kw)
        return muid

    def chat_llm(_, use_tools=True) -> ollama.ChatResponse:
        retries = -1
        messages = _.materialize_history()
        for m in messages:
            print("  ==  ", m)
            pass
        while 1:
            retries += 1
            if retries > 3:
                print("TOO MANY RETRIES")
                raise SystemExit(1)
            tools = _.tools if use_tools else []
            #tools = []
            #if use_tools:
            ret = ollama.chat(model=_.model, messages=messages,
                              tools=  tools, stream=True,
                              format='json')
            #else:
            #    ret = ollama.chat(model=_.model, messages=messages,
            #                      stream=True,
            #                      format='json')
            #    pass
            if type(ret).__name__ == 'generator':
                return ret
            return [ ret ]
        
    def chat_round(_, content, role='user'):
        """
        a round is where each conversationalist takes a turn
        in LLM world, this is a user comment followed by
        as assistant comment with optional tool calling in
        the middle
        """

        phase = 0

        # save the message
        _.append_hist(role, content, phase=phase)

        # process results
        for msg in _.chat_llm():

            phase = 10
            
            message, done = msg.message, msg.done

            if not message:
                print("NO MESSAGE")
                raise exit(1)

            if message.get('content') is None and not message.tool_calls:
                print("THIS NO CONTENT AND NO TOOL CALLS (maybe an image?)")
                raise exit(5)

            if message.content is not None and not message.tool_calls:
                _.append_hist(message.role, message.content, done=done, phase=phase)
                continue

            assert( len(message.tool_calls) == 1 )

            tool_call = message.tool_calls[0].function

            name, arguments, done = \
                (tool_call.name, tool_call.arguments, done)

            if name == 'respond_to_user':
                # DON'T call a function here...
                # we'll just handle it right here ourselves
                _.append_hist(message.role, content = arguments['message'],
                              done=done, phase=phase)
                continue

            function_to_call = getattr(_.funcs, name, '')

            if not function_to_call:
                print('Function', name, 'not found')
                raise exit(1)

            phase = 20
            
            tool_calls = [dict(function = dict(name=name,
                                               arguments=arguments))]
            _.append_hist('tool', tool_calls=tool_calls, phase=phase)
            
            phase = 21

            try:
                output = function_to_call(**arguments)
            except:
                
                phase = 29

                output = _.error_output()
                pass

            _.append_hist('assistant', output, tool_name=name, phase=phase)

            phase = 30

            use_tools = False
            use_tools = True
            for msg in _.chat_llm(use_tools=use_tools):

                done, message = msg.done, msg.message
                print("TC MESSAGE", done, message)

                if not message:
                    raise SystemExit(1)

                if message.tool_calls:
                    raise Exception('wtf0')

                _.append_hist(message.role, message.content, 
                              done=done, phase=phase)
                
            else: # for msg in _.chat_llm(use_tools=use_tools):

                pass
            
        else: # for msg in _.chat_llm():
            
            phase = 99
            
            _.pub_content('root', done=True, superdone=True, phase=phase)
            
            pass
        pass # def chat_round(_, content, role='user'):
    pass # class EphemeralSessionProxy:
