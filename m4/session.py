from typing import Any, Dict, List, Optional, Union, cast
import os, time, json, websocket, ollama
import db_sync as db
from logging_setup import get_logger
import traceback


logger = get_logger(__name__)


def generator_wrap(x):
    if type(x).__name__ == 'generator':
        return x
    return [ x ]


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


STREAM = bool(os.getenv('STREAM', True))
THINK =  bool(os.getenv('THINK',  True))
#THINK = os.getenv('THINK',False)

NAME = os.getenv('NAME','llm')
IN_CHANNEL  = NAME+'-in'
OUT_CHANNEL = NAME+'-out'
WS_BASE = "ws://localhost:5002/ws"

'''def append_tool1(_, name, arguments, **kw):
        tool_calls = [ dict( function = dict( name=name,
                                              arguments=arguments)) ]
        _id = _.append_hist('', role='assistant', tool_calls=tool_calls, **kw)
    def append_tool2(_, name, content, **kw):
        _id = _.append_hist(content=str(content), role='tool', tool_name=name, **kw)
'''

class EphemeralSessionProxy:
    
    def __init__(_, uuid, session_id, funcs, ws, model, tools):
        _.uuid, _.session_id, _.funcs = uuid, session_id, funcs
        _.ws,   _.model,      _.tools =  ws,  model,      tools
        pass
    
    def materialize_history(_):
        """this thin wrapper will grow into its own subststem"""
        ret = list( db.load_simplified_convo(_.session_id) )
        print("--------->MATHIST")
        for m in ret:
            print("  M", m)
            pass
        print("<---------")
        return ret
    
    def append_hist(_, content='', role='user', kind='history', **kw):
        _.seq += 1
        kw.update(dict(content=content, role=role, kind=kind, seq=_.seq))
        muid = db.create_memory(session_id=_.session_id, user_id=_.uuid, **kw)
        euid = db.create_memory_edge(muid, _.session_id, 'belongs_to')
        pub(_.ws, _.out_channel, **kw)
        return muid
    
    def ollama_chat(_, **kw):
        max_retries = 3
        retries = 0
        while retries < max_retries:
            try:
                ret = ollama.chat(messages=_.materialize_history(),
                                  model=_.model, tools=_.tools, **kw)
                return generator_wrap(ret)
            except:
                retries += 1
                pass
            pass
        pass
    
    def filter_tool_calls(_, done, message, accumulator):
        _tool_calls = []
        for call in (message.tool_calls or []):
            print("TC", call)
            name, arguments = call.function.name, call.function.arguments
            if name == 'respond_to_user':
                _.respond_to_user(done, message, arguments['message'], None)
                continue                
            funcall = dict( function=dict( name=name, arguments=arguments ) )
            _tool_calls.append( funcall ) 
            accumulator.append( funcall )
            pass
        return _tool_calls
    
    def respond_to_user(_, done, message, content, tool_calls):
        if not done and not content and not tool_calls and not message.get('thinking'):
            print("SUPPRESS", (done, content, message.role), message.thinking, tool_calls)
            return
        kw = dict(done=done)
        if tool_calls is not None:        kw['tool_calls'] = tool_calls
        if thinking := message.thinking:  kw['thinking'] = thinking
        if                         done:  kw['autotool'] = bool(tool_calls)
        _.append_hist(content=content, role=message.role, **kw)
        return    

    def chat_round(_, content=None, channel=None, role='user', auto_tool=True):
        if channel is not None:
            _.out_channel = channel
            pass
        if content is not None:
            _.seq = 999
            _.append_hist(content=content, role=role, seq=_.seq)
            pass
        while 1:
            all_tool_calls = []
            for msg in _.ollama_chat(stream=STREAM, think=THINK):
                message, done = msg.message, msg.done
                funcalls = _.filter_tool_calls(done, message, all_tool_calls)
                _.respond_to_user(done, message, message.content, funcalls)
                pass
            if not all_tool_calls:
                print("NO MORE TOOLS, WE'RE DONE WITH THIS ROUND")
                #_.append_hist(role='round', superdone=True)
                #print("BYE!")            
                return
            for tc in all_tool_calls:
                try:
                    tool_name = tc['function']['name']
                    arguments = tc['function']['arguments']
                    print("TOOL CALL", (tool_name, arguments))
                    function_to_call = getattr(_.funcs, tool_name)
                    content = function_to_call(**arguments)
                except:
                    content = traceback.format_exc()
                    print("\\ERROR", '*'*40)
                    print(content)
                    print( "/ERROR", '*'*40)
                    pass
                _.append_hist(role='tool', tool_name=tool_name, content=content)
                pass

            if not auto_tool:
                print("SAVED ALL THE TOOL OUTPUT, BUT AUTOTOOL IS OFF")
                break
            
            # do it again!
            print("SAVED ALL THE TOOL OUTPUT, PRIMED FOR ANOTHER LLM CHAT RUN (RECURSE)!")
            #_.chat_round()


"""
            #pass
            
            continue
            if not message:
                print("NO MESSAGE")
                raise exit(1)
            if message.get('content') is None and not message.tool_calls:
                print("THIS NO CONTENT AND NO TOOL CALLS (maybe an image?)")
                raise exit(5)
            if message.content is None:
                print(done, message)
                print(" **** MSG.CONTENT IS NONE ****")
                content_is_none
                raise
            if message.content and message.tool_calls:
                print(done, message)
                print(" **** MSG.CONTENT AND MSG.TOOL_CALLS ARE BOTH NON-NONE ****")
                content_and_tool_calls_are_non_none
                raise
            if message.content:
                respond_to_user(message.content)
                continue
            if message.tool_calls:
                _tool_calls = []
                for call in message.tool_calls:
                    tool_call = call.function
                    name, arguments = tool_call.name, tool_call.arguments
                    #if name == 'respond_to_user':
                    #    respond_to_user(tc.arguments['message'])
                    #    continue 
                    _tool_call = dict( function = dict( name=name,
                                                        arguments=arguments ) )
                    _tool_calls.append( _tool_call )
                    tool_calls.append( (name, arguments) )
                    pass
                else:
                    pass
                _.append_hist(message.content, role=message.role, tool_calls=_tool_calls)
                _.pub_content(message.content, role=message.role, tool_calls=_tool_calls)
            else:
                pass
            pass

        for tool_name, arguments in tool_calls:
            print("DEAL WITH THIS", (tool_name, arguments))
            pass

        return
            
'''
        if 0:
            phase = 20.1

            if message.content is not None and not message.tool_calls:

                kw = dict(phase=phase, done=done, active=True)
                if thinking := message.thinking:
                    kw['thinking'] = thinking
                    pass
                _.append_hist(message.content, message.role, **kw)
                _.pub_content(message.content, message.role, **kw)
                continue

            phase = 21.1

            assert( len(message.tool_calls) == 1 )

            tool_call = message.tool_calls[0].function

            name, arguments, done = \
                (tool_call.name, tool_call.arguments, done)

            if name == 'respond_to_user':
                # DON'T call a function here, we'll just handle it right here ourselves
                role = 'assistant'
                content = arguments['message']

                kw = dict(phase=phase, done=done, active=True)

                _.append_hist(content, role, **kw)
                _.pub_content(content, role, **kw)

                continue

            phase = 31.1
        phase = 31.1

            function_to_call = getattr(_.funcs, name, '')

            if not function_to_call:
                print('Function', name, 'not found')
                raise exit(1)

            _.append_hist(role='assistant', phase=phase, active=True,
                          tool_calls = [ dict( function = dict( name=name,
                                                                arguments=arguments)) ])

            try:
                output = function_to_call(**arguments)
            except:
                output = traceback.format_exc()
                print("\\ERROR", '*'*40)
                print(output)
                print( "/ERROR", '*'*40)
                pass

            phase = 32.1
                        
            _.append_hist(role='tool', tool_name=name, content=str(output), phase=phase, active=True)

            pass # end first chat loop

        if 0:
        
            for tmsg in ollama.chat(model=_.model,
                                    messages=_.materialize_history(),
                                    tools=_.tools,
                                    stream=True,
                                    think=True,
                                    #format='json',
                                    ):

                tdone, tmessage = tmsg.done, tmsg.message

                if not tmessage:
                    raise exit(1)

                elif not tmessage.content and not tmessage.tool_calls and tmessage.get('thinking'):

                    phase = 41
                    
                    kw = dict(phase=phase, done=tdone, role=tmessage.role)
                    if thinking := tmessage.thinking:
                        kw['thinking'] = thinking
                        pass
                    _.append_hist(tmessage.content, active=False, **kw)
                    _.pub_content(tmessage.content, active=False, **kw)

                elif     tmessage.content and not tmessage.tool_calls:

                    phase = 42.1
                    
                    kw = dict(phase=phase, done=tdone, role=tmessage.role)
                    if thinking := tmessage.thinking:
                        kw['thinking'] = thinking
                        pass
                    _.append_hist(tmessage.content, active=True,  **kw)
                    _.pub_content(tmessage.content, active=True,  **kw)

                elif not tmessage.content and     tmessage.tool_calls:

                    print("2deep?")
                    print(tmessage)
                    
                    raise Exception('too deep')

                else:
                    
                    print("ORPHAN", tmessage)
'''
"""
