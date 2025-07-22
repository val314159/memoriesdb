#!/usr/bin/env python3
from gevent import monkey as _;_.patch_all()
import os, json, gevent, gevent.queue
from subagent import SubAgentBase, OUT_CHANNEL
from subagent import IN_CHANNEL
#import funcs2 as funcs
#from session import EphemeralSessionProxy as ESP, chat_round
from db_sync import get_user_sessions

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
    #def __init__(_,tools=funcs.Tools, model=os.getenv('MODEL', 'llama3.1')):
    #    _.tools, _.model, _.models, _.children = tools, model, dict(), dict()
    #    return
    #def kill_if_possible(_, key):
    #    if kid:= _.children.pop(key, None):
    #        gevent.kill(kid)
    #        print("INTERRUPT THE CURRENT PROCESS", key, kid)
    #        pass
    #    return
    #def _pub(_, content, uuid, session, model='', toolset='', **kw):
    #    key = ( uuid, session )
    #    model = model or _.models.get(key) or _.model
    #    _.models[key] = model
    #    _.kill_if_possible(key)
    #    def bg_pub():
    #        sess = ESP(uuid, session, funcs, _.ws(), model, _.tools)
    #        chat_round(sess, content, OUT_CHANNEL)
    #        del _.children[key]
    #        return
    #    _.children[key] = gevent.spawn(bg_pub)
    #    return
    def _pub(_, content, uuid, *args, **kw):
        print("_PUB", content, uuid, (args, kw))
        results = []
        for row in get_user_sessions(uuid):
            print(row)
            print(f"Session {row['id']}: {row['content']}")
            results.append([str(row['id']), row['content']])
            pass
        pub(_.ws(), OUT_CHANNEL, content, results=results)
        return
    pass
if __name__ == '__main__':
    DbSvr().main()
