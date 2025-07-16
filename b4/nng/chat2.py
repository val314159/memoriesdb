#!/usr/bin/env python3
'''
Usage:
    chat <uuid> <session_id>
    chat <uuid>
    chat <uuid> ( -o | --orig )
    chat (-h | --help | -v | --version)

Options:
    -o, --orig     Originate brand new convo
    -h, --help     Show this screen and exit.
    -v, --version  Show this screen and exit.
    --baud=<n>   Baudrate [default: 9600]
'''
from gevent import monkey as _;_.patch_all()
import os, sys, time, json, websocket, gevent, docopt
from gevent.fileobject import FileObject

import asyncio
import asyncio_gevent

# make gevent/asyncio work together
asyncio.set_event_loop_policy(asyncio_gevent.EventLoopPolicy())


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

        #content = ''
        #pub(ws, CH_IN, content, kind='session', xyz=200)

        while content := readline():
            role = 'user'
            if content.startswith('system: '):
                role = 'system'
                content = content[len('system: '):]
                pass
            pub(ws, CH_IN, content, role=role, session=session_id)
            pass
        return print("EOF")

    gevent.spawn(ws_loop)
    return fe_loop()


from db_ll_sync import *

from db_sync import check_valid_uuid

if __name__=='__main__':
    args = docopt.docopt(__doc__, version="1.0.1")
    print("ARGS", args)

    uuid = args['<uuid>']
    print("USER", uuid)

    if args['--orig']:

        print("YES, ORIG")
        check_valid_uuid(uuid)

        def originate_session(forked_from=None):
            print("originate_session():", 
                  (forked_from,))
            if forked_from:
                raise Exception("DONT KNOW HOW "
                                "TO DO THIS YET")

            print("ok let's make a new session")
            
        originate_session()

        print("skip main...")
    
        # main()

    else:
        uuid = args['<uuid>']
        check_valid_uuid(uuid)

        main()
        #print("NOO, BAD ARGS", args)
        #raise SystemExit(1)

    # main()
