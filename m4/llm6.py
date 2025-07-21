#!/usr/bin/env python3
from gevent import monkey as _;_.patch_all()
import os, gevent, gevent.queue
from subagent import SubAgentBase, OUT_CHANNEL
import funcs2 as funcs
from session import EphemeralSessionProxy as ESP, chat_round
class Convo(SubAgentBase):
    def __init__(_,tools=funcs.Tools, model=os.getenv('MODEL', 'llama3.1')):
        _.tools, _.model, _.children = tools, model, dict()
        return
    def _kill_if_possible(_, key):
        if kid:= _.children.pop(key, None):
            gevent.kill(kid)
            print("INTERRUPT THE CURRENT PROCESS", key, kid)
            pass
        return
    def _pub(_, content, uuid, session, model='', toolset='', **kw):
        key = ( uuid, session )
        _._kill_if_possible(key)
        args = (_._bg_pub, key, content, uuid, session, model, toolset)
        _.children[key] = gevent.spawn(*args)
        return
    def _bg_pub(_, key, content, uuid, session, model, toolset):
        sess = ESP(uuid, session, funcs, _.ws(), model or _.model, _.tools)
        chat_round(sess, content, OUT_CHANNEL)
        del _.children[key]
        return
    pass
if __name__ == '__main__':
    Convo().main()
