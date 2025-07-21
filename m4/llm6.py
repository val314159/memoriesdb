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
        def bg_pub():
            sess = ESP(uuid, session, funcs, _.ws(), model or _.model, _.tools)
            chat_round(sess, content, OUT_CHANNEL)
            del _.children[key]
            return
        _._kill_if_possible(key)
        _.children[key] = gevent.spawn(bg_pub)
        return
    pass
if __name__ == '__main__':
    Convo().main()
