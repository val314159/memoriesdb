from typing import Any, Dict, List, Optional, Union, cast
import os, time, json, websocket, ollama, traceback, db_sync, logging_setup
from config import STREAM, THINK, TOOLS
logger = logging_setup.get_logger(__name__)
def pub(ws, channel, content='', **kw):
    ws.send(channel)
    return ws.send(json.dumps(dict(method='pub',
                                   params=dict(channel=channel,
                                               content=content, **kw))))
def is_generator(x):
    return type(x).__name__ == 'generator'
def is_blank_message(message):
    return not ( message.get( 'tool_calls' ) or
                 message.get( 'content'    ) or
                 message.get( 'images'     ) or
                 message.get( 'done'       ) )
def call_tool(tool_name, funcs=None, **kw):
    print("TOOL CALL", (tool_name, kw))
    try:
        return getattr(funcs, tool_name)(**kw)
    except:
        content = traceback.format_exc()
        print("\\ERROR", '*'*40)
        print(content)
        print( "/ERROR", '*'*40)
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
    for msg in db_sync.load_simplified_convo(_.session_id):
        if msg.get('thinking'):
            del msg['thinking']
            pass
        if is_blank_message(msg):
            continue
        yield msg
        print("===M", msg)
        pass
    return print("<---------")
def append_hist(_, content='', role='user', kind='history', **kw):
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
            results = ollama.chat(**kw)
        except:
            retries += 1
            continue
        return results if is_generator(results) else [ results ]
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
        for msg in llm_messages:
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
            content = call_tool(fn.name, fn.arguments, _.funcs)
            append_hist(_, content=content, role='tool', tool_name=fn.name)
