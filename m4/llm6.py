#!/usr/bin/env python3
'''
Let's assume we only have one convo at once!
and we'll use a JSON file!
whee!
'''
from gevent import monkey as _;_.patch_all()
import os, sys, time, json, websocket, ollama
import funcs2 as funcs

from session import EphemeralSessionProxy
import db_sync as db

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

    def got_init(_, params):
        print("INIT", params)
        pass

    def got_pub(_, params):
        return EphemeralSessionProxy(params['uuid'], params['session'], funcs,
                                     _.ws, _.model, _.tools, OUT_CHANNEL
                                     ).chat_round(params['content'])

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
