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
TOOLS =  bool(os.getenv('TOOLS',  True))
#THINK = os.getenv('THINK',False)

NAME = os.getenv('NAME','llm')
IN_CHANNEL  = NAME+'-in'
OUT_CHANNEL = NAME+'-out'
WS_BASE = "ws://localhost:5002/ws"


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
                if TOOLS:
                    kw['tools'] = _.tools
                    pass
                messages = _.materialize_history()
                ret = ollama.chat(messages=messages, model=_.model, **kw)
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

            images = []
            if 'IMAGE==>' in content:
                content, image = content.strip().split('IMAGE==>', 1)
                images = [ image ]
                pass
            _.append_hist(content=content, role=role, seq=_.seq, images=images)
            pass
            
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
