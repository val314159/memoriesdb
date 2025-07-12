#!/usr/bin/env python3
from gevent import monkey as _;_.patch_all()
import os, sys, time, json, websocket, gevent
from gevent.fileobject import FileObject

#from util import load_history_from_yml
#messages = load_history_from_yml()
#for m in messages:
#    print("MESSAGE:", m)
#    pass
#print('---')

# This makes stdin's FD non-blocking and replaces sys.stdin with
# a wrapper that is integrated into the event loop
stdin = FileObject(sys.stdin)


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


CH = os.getenv('CH', 'llm')
    
CH_IN  = os.getenv('CH_IN', CH+'-in')
CH_OUT = os.getenv('CH_OUT',CH+'-out')

CHANNELS = [CH_OUT]

WS_BASE = f"ws://localhost:5002/ws"
WS_ARGS = '?c='+'&c='.join(CHANNELS)


def main():

    def readline():
        content = '\n'
        while content == '\n':
            print("user>", end=' ')
            content = stdin.readline()
            pass
        return content

    ws = websocket.WebSocket()
    ws.connect(WS_BASE + WS_ARGS)

    def ws_once():
        msg = recv(ws)
        method = msg.get('method')
        params = msg.get('params',{})
        if   method=='initialize':
            print("INIT", params)
        elif method=='pub':
            print("PUB", params)                    
        else:
            print("*"*80)
            print("ERROR, BAD PACKET", msg)
            print("*"*80)
            pass
        pass
    
    def ws_loop():
        while 1:
            try:
                ws_once()
                time.sleep(0.2)
            except:
                print("SERVER EOF, EXIT OUT ALL THE WAY")
                raise sys.exit(2)
            pass
        pass
    
    def fe_loop():
        while content := readline():
            role = 'user'
            if content.startswith('system: '):
                role = 'system'
                content = content[len('system: '):]
                pass
            pub(ws, CH_IN, content, role=role)
            pass
        return print("EOF")

    gevent.spawn(ws_loop)
    return fe_loop()


if __name__=='__main__':
    main()
