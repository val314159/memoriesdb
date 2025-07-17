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

    def pub_content(_, content, role, channel = None, **kw):
        pub(_.ws, channel or _.out_channel, content, role=role, **kw)

    def append_hist(_, content, role='user', **kw):
        muid = db.create_memory(session_id=_.session_id,
                                user_id=_.uuid,
                                content=content,
                                role=role,
                                kind='history',
                                **kw)
        euid = db.create_memory_edge(muid, _.session_id, 'belongs_to')
        return muid

    def append_user(_, content, role, **kw):
        _id = _.pub_content(content, role, **kw)
        _id = _.append_hist(content, role, **kw)
        return _id

    def append_tool(_, role, output='', **kw):
        _id = _.pub_content(str(output), role, **kw)
        _id = _.append_hist(str(output), role, **kw)
        return _id

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

        # save the message
        _.append_user(content, role, phase=0)

        # process results
        for msg in _.chat_llm():
            message, done = msg.message, msg.done

            if not message:
                print("NO MESSAGE")
                raise exit(1)

            if message.get('content') is None and not message.tool_calls:
                print("THIS NO CONTENT AND NO TOOL CALLS (maybe an image?)")
                raise exit(5)

            if message.content is not None and not message.tool_calls:
                _.append_hist(message.content, message.role, done=done, phase=1)
                _.pub_content(message.content, message.role, done=done, phase=1)
                continue

            assert( len(message.tool_calls) == 1 )

            tool_call = message.tool_calls[0].function

            name, arguments, done = \
                (tool_call.name, tool_call.arguments, done)

            if name == 'respond_to_user':
                # DON'T call a function here...
                # we'll just handle it right here ourselves
                role = 'assistant'
                content = arguments['message']
                _.append_hist(content, role, done=done, phase=1)
                _.pub_content(content, role, done=done, phase=1)        
                continue

            function_to_call = getattr(_.funcs, name, '')

            if not function_to_call:
                print('Function', name, 'not found')
                raise exit(1)

            tool_calls = [ dict( function = dict( name=name,
                                                  arguments=arguments)) ]
            _.append_tool('tool', tool_calls=tool_calls, phase=3)
            
            try:
                output = function_to_call(**arguments)
            except:
                output = traceback.format_exc()
                print("\\ERROR", '*'*40)
                print(output)
                print( "/ERROR", '*'*40)
                pass

            _.append_tool('assistant', output, tool_name=name, phase=4)

            use_tools = False
            use_tools = True
            for msg in _.chat_llm(use_tools=use_tools):

                message, done = msg.message, msg.done

                if not message:
                    raise exit(1)

                elif     message.content and not message.tool_calls:
                    _.append_hist(message.content, message.role, done=done, phase=5)
                    _.pub_content(message.content, message.role, done=done, phase=5)

                elif not message.content and     message.tool_calls:

                    print("2deep?")
                    print(message)
                    
                    raise Exception('too deep')

                elif not done:
                    raise Exception('wtf')
                else:
                    pass
            else:
                pass
        else:
            # final!
            _.pub_content('', message.role, superdone=done, phase=9)
            pass
        pass # def chat_round(_, content, role='user'):
    pass # class EphemeralSessionProxy:
