from typing import Any, Dict, List, Optional, Union, cast
import os, time, json, websocket, ollama, traceback
import db_sync as db
from logging_setup import get_logger
from config import STREAM, THINK, TOOLS
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
class EphemeralSessionProxy:
    @staticmethod
    def call_tool(tool_name, funcs=None, **kw):
        #print("TOOL CALL", (tool_name, kw))
        function_to_call = getattr(funcs, tool_name)
        return function_to_call(**kw)
    @staticmethod
    def report_error():
        content = traceback.format_exc()
        print("\\ERROR", '*'*40)
        print(content)
        print( "/ERROR", '*'*40)
        return content
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
                return   ret \
                    if type(ret).__name__ == 'generator' else \
                       [ ret ]
            except:
                retries += 1
                pass
            pass
        pass    
    def respond_to_user(_, done, message, content, tool_calls):
        #if not done and not content and not tool_calls and not message.get('thinking'):
        #    return print("SUPPESS", (done, content, message.role),
        #                 message.thinking, tool_calls)
        kw = dict(done=done)
        if tool_calls is not None:        kw['tool_calls'] = tool_calls
        if thinking := message.thinking:  kw['thinking'] = thinking
        if                         done:  kw['autotool'] = bool(tool_calls)
        return _.append_hist(content=content, role=message.role, **kw)
    def filter_tool_calls(_, done, message):
        for call in (message.tool_calls or []):
            #print("TC", call)
            name, arguments = call.function.name, call.function.arguments
            if name == 'respond_to_user':
                _.respond_to_user(done, message, arguments['message'], None)
                continue                
            yield dict( function=dict( name=name, arguments=arguments ) )
            pass
        pass
    def append_llms(_, llm_messages):
        all_tool_calls = []
        for msg in llm_messages:
            message, done = msg.message, msg.done
            funcalls = list( _.filter_tool_calls(done, message) )
            _.respond_to_user(done, message, message.content, funcalls)            
            all_tool_calls.extend( funcalls )
            pass
        return all_tool_calls
    def append_user(_, content, role, **kw):
        _.seq, images = 999, []
        if 'IMAGE==>' in content:
            content, image = content.strip().split('IMAGE==>', 1)
            images.append( image )
            pass
        return _.append_hist(content=content, role=role, seq=_.seq, **kw)
    def chat_round(_, content='', channel='', role='user', auto_tool=True):
        if channel: _.out_channel = channel
        if content: _.append_user(content=content, role=role)
        while llm_messages:= _.ollama_chat(stream=STREAM, think=THINK):
            # can we save these somewhere and mark them?
            all_tool_calls = _.append_llms(llm_messages)
            if not all_tool_calls:
                return print("NO MORE TOOLS, WE'RE DONE WITH THIS ROUND")
            for tool_call in all_tool_calls:
                fn = tool_call['function']
                try   : content = _.call_tool(fn.name, fn.arguments, _.funcs)
                except: content = _.report_error()
                _.append_hist(content=content, role='tool', tool_name=fn.name)
            if not auto_tool:
                return print("SAVED ALL THE TOOL OUTPUT, BUT AUTOTOOL IS OFF")
            print("SAVED ALL THE TOOL OUTPUT, PRIMED FOR ANOTHER LLM CHAT RUN (RECURSE)!")
