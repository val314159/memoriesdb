#!/usr/bin/env python3
'''
Let's assume we only have one convo at once!
and we'll use a JSON file!
whee!
'''
from gevent import monkey as _;_.patch_all()
import os, sys, time, json, websocket, ollama
import funcs2 as funcs

from session import EphemeralSessionProxy as ESP


NAME = os.getenv('NAME','llm')
IN_CHANNEL  = NAME+'-in'
OUT_CHANNEL = NAME+'-out'
WS_BASE = "ws://localhost:5002/ws"


class SubAgentBase:

    def connect_ws(_):
        '''we do it this way so error don't leave garbage in _.ws'''
        ws = websocket.WebSocket()
        ws.connect(f'{WS_BASE}?c={IN_CHANNEL}')
        _.ws = ws
        pass

    def pub(_, params):
        raise Exception('NYI')
    
    def main(_):
        _.connect_ws()
        while 1:
            print("Waiting on socket...")
            raw = _.ws.recv()
            if not raw:
                raise EOFError
            msg = json.loads(raw)
            print("Got", (msg,), "!")
            method = msg.get('method')
            params = msg.get('params',{})
            if method=='initialize':  
                print("INIT", params)
            elif method=='pub':
                _.pub(params)
            else:
                print("*"*80)
                print("ERROR, BAD PACKET", msg)
                print("*"*80)
                pass
            pass
        print("EOF")
        return

    pass


class Convo(SubAgentBase):

    def __init__(_,tools=funcs.Tools, model='llama3.1'):
        _.tools, _.model, _.ws = tools, model, None
        pass

    def pub(_, params):
        sess = ESP(params['uuid'],
                   params['session'],
                   funcs, _.ws, _.model,
                   _.tools, OUT_CHANNEL)
        sess.chat_round(params['content'])
        pass
    
    pass

if __name__=='__main__':
    Convo().main()
