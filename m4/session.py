from typing import Any, Dict, List, Optional, Union, cast
import os, time, json, websocket, ollama, traceback, db_sync, logging_setup
from config import STREAM, THINK, TOOLS
logger = logging_setup.get_logger(__name__)
_ollama_connection = None
def ollama_connection():
    global _ollama_connection
    if not _ollama_connection:
        _ollama_connection = ollama.Client()
        pass
    return _ollama_connection
def pub(ws, channel, content='', **kw):
    ws.send(channel)
    return ws.send(json.dumps(dict(method='pub',
                                   params=dict(channel=channel,
                                               content=content, **kw))))
def   is_generator(x): return type(x).__name__ == 'generator'
def wrap_generator(x): return x if is_generator(x) else [ x ]
def is_blank_message(message): return not ( message.get( 'tool_calls' ) or
                                            message.get( 'content'    ) or
                                            message.get( 'images'     ) or
                                            message.get( 'done'       ) )
def call_tool(funcs, tool_name, **kw):
    print("TOOL CALL", (tool_name, kw))
    try:
        return getattr(funcs, tool_name)(**kw)
    except:
        content = traceback.format_exc()
        print("\\TOOL ERROR", '*'*40)
        print(content)
        print( "/TOOL ERROR", '*'*40)
        return content
    pass
class EphemeralSessionProxy:
    def __init__(_, uuid, session_id, funcs, ws, model, tools):
        _.uuid, _.session_id, _.funcs = uuid, session_id, funcs
        _.ws,   _.model,      _.tools =  ws,  model,      tools
        pass
    pass
def materialize_history(_):
    """this thin wrapper will grow into its own subsystem"""
    print("--------->MATHIST")
    #for msg in db_sync.load_simplified_convo(_.session_id):
    msgs = db_sync.load_simplified_convo(_.session_id)
    print("--------->MATHIST2")
    for msg in msgs:
        if msg.get('thinking'):
            del msg['thinking']
            pass
        if is_blank_message(msg):
            continue
        yield msg
        print("===M", msg)
        pass
    return print("<---------")
def append_hist(_, content='', role='user', kind='partial', **kw):
    _.seq += 1
    kw.update(dict(content=content, role=role, kind=kind, seq=_.seq))
    muid = db_sync.create_memory(session_id=_.session_id, user_id=_.uuid, **kw)
    euid = db_sync.create_memory_edge(muid, _.session_id, 'belongs_to')
    pub(_.ws, _.out_channel, **kw)
    return muid
def ollama_chat(_, stream=STREAM, think=THINK, tools=TOOLS, max_retries=3, retries=0):
    messages = list( materialize_history(_) )
    kw = dict(messages=messages, model=_.model, stream=stream, think=think)
    if tools: kw['tools'] = _.tools
    while retries < max_retries:
        try:
            return wrap_generator( ollama_connection().chat(**kw) )
        except:
            retries += 1
            pass
        pass
    pass
def _respond_to_user(_, done, message, content, tool_calls, **kw):
    if tool_calls:                   kw['tool_calls'] = tool_calls
    if thinking:= message.thinking:  kw[ 'thinking' ] = thinking
    if    done    is not None:       kw[   'done'   ] = done
    if    done:                      kw[ 'autotool' ] = bool(tool_calls)
    return append_hist(_, content=content, role=message.role, fn='respond_to_user', **kw)
def _filter_tool_calls(_, done, message):
    for call in (message.tool_calls or []):
        name, arguments = call.function.name, call.function.arguments
        if name == 'respond_to_user':
            _respond_to_user(_, done, message, arguments['message'], None)
            continue
        yield dict( function=dict( name=name, arguments=arguments ) )
        pass
    pass
def _append_user(_, content, role, **kw):
    _.seq = 999
    if 'IMAGE==>' in content:
        content, image = content.strip().split('IMAGE==>', 1)
        kw['images'] = [ image ]
        pass
    return append_hist(_, content=content, role=role, seq=_.seq, fn='append_user', **kw)
def chat_round(_, content='', channel='', role='user', auto_tool=True):
    if channel: _.out_channel = channel
    if content: _append_user(_, content=content, role=role)
    tool_calls = [] # keep track of calls we need to do
    while llm_messages:= ollama_chat(_):
        print("LLM MESSAGES", llm_messages)
        def read_messages():
            n = -1
            try:
                for n, msg in enumerate(llm_messages):
                    yield msg
            except:
                import traceback
                print("\\LLM ERROR", '*'*40)
                traceback.print_exc()
                print( "/LLM ERROR", '*'*40)
                print( "=LLM ERROR", n, n, n, n, n, n, n)
                pass
            pass
        for msg in read_messages():
            funcalls = list( _filter_tool_calls(_, msg.done, msg.message) )
            tool_calls.extend( funcalls )
            _respond_to_user(_, msg.done, msg.message,
                             msg.message.content, funcalls, scan=1)
            pass
        if not auto_tool:
            return print("NO AUTO_TOOL...WE'RE DONE WITH THIS ROUND")
        if not tool_calls:
            return print("NO MORE TOOLS, WE'RE DONE WITH THIS ROUND")
        while tool_calls:
            fn = tool_calls.pop(0)['function']
            content = call_tool(_.funcs, fn['name'], **fn['arguments'])
            append_hist(_, content=content, role='tool', tool_name=fn['name'])
