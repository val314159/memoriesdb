#!/usr/bin/env python3
from gevent import monkey as _;_.patch_all()
import os, json, gevent, gevent.queue
from subagent import SubAgentBase, OUT_CHANNEL
from db_sync import get_user_sessions, load_simplified_convo

YAML_FILE = 'chat2.yml'

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

class DbSvr(SubAgentBase):
    def _pub(_, content, uuid, session, *args, **kw):
        print("_PUB", content, uuid, (args, kw))
        results = []
        if   content=='listConvos':
            for row in get_user_sessions(uuid):
                print(row)
                print(f"Session {row['id']}: {row['content']}")
                results.append([str(row['id']), row['content']])
        elif content== 'shortHistory':
            print("LOAD SHORT HISTORY", uuid, session)
            for row in load_simplified_convo(session, True):
                row.pop('thinking', '')
                print("   ROW", row)
                if row['content'] or row['done'] or row.get('images'):
                    results.append(row)
                    if len(row) >= 16:
                        pub(_.ws(), OUT_CHANNEL, content, results=results)
                        results = []
                        pass
                    pass
                pass
        elif content== 'newConvo':
            from load_convo import save_convo
            results.append(str(save_convo(YAML_FILE)))
        else:
            print("WTF IS THIS", content)
            wtf
            return
        pub(_.ws(), OUT_CHANNEL, content, results=results)
        return
    pass
if __name__ == '__main__':
    DbSvr().main()
