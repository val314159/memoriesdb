#!/usr/bin/env python3
'''
Usage:
    chat <uuid> <session_id>
    chat (-h | --help | -v | --version)

Options:
    -h, --help     Show this screen and exit.
    -v, --version  Show this screen and exit.
    --baud=<n>     Baudrate [default: 9600]
    <session_id>   session_id or LAST
    <uuid>          a user_id or TEST
'''
from gevent import monkey as _;_.patch_all()
import os, sys, time, json, websocket, gevent, docopt
from gevent.fileobject import FileObject
from uuid import UUID

from db_sync import check_valid_uuid, get_last_session, get_current_user_id


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
    ws.send(channel)
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
            if   content == 'q\n':
                print(">> Bye!", flush=True)
                raise SystemExit(0)
            elif content == 'j\n':
                content = "Tell me a joke."
            elif content == 'a\n':
                content = "12345 + 54321 = what?\n"
            elif content == 'c\n':
                content = "What is this?\nIMAGE==>./Cute_cat.jpg"
            elif content == 'd\n':
                content = "What is this?\nIMAGE==>./Cute_dog.jpg"
            else:
                pass
        else:
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
            kw = dict(role='user', uuid=uuid, session=session_id)
            if content.startswith('system: '):
                kw['role'], content = content.strip().split(': ', 1)
                pass
            #if 'IMAGE==>' in content:
            #    content, kw['image'] = content.strip().split('IMAGE==>')
            #    pass
            pub(ws, CH_IN, content, **kw)
            pass
        print("EOF")
        return

    gevent.spawn(ws_loop)
    return fe_loop()


def _get_user_id():
    uuid = args['<uuid>']
    try:
        assert( uuid=='TEST' or UUID(uuid) )
    except:
        print("Bad user_id (should be a valid uuid or TEST):", session_id)
        raise SystemExit(1)
    if uuid == 'TEST':
        uuid = get_current_user_id()
        pass
    print("UUID?", uuid)
    check_valid_uuid(uuid)
    print("UUID!", uuid)
    return uuid
    
def _get_session_id():
    session_id = args['<session_id>']
    try:
        assert( session_id=='LAST' or UUID(session_id) )
    except:
        print("Bad session_id (should be a valid uuid, or LAST):", session_id)
        raise SystemExit(1)
    if session_id == 'LAST':        
        row = get_last_session(uuid)
        print("ROW:", row)
        session_id = str(row['id'])
    else:
        # validate session id here?
        pass
    print("SESS", session_id)
    return session_id

if __name__=='__main__':
    args = docopt.docopt(__doc__, version="1.0.1")
    uuid = _get_user_id()
    session_id = _get_session_id()
    main()
