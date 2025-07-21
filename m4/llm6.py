#!/usr/bin/env python3
from gevent import monkey as _;_.patch_all()
import os, gevent, gevent.queue
from subagent import SubAgentBase, OUT_CHANNEL
import funcs2 as funcs
from session import EphemeralSessionProxy as ESP, chat_round
class Convo(SubAgentBase):
    def __init__(_,tools=funcs.Tools, model=os.getenv('MODEL', 'llama3.1')):
        _.tools, _.model = tools, model
        _.child = None
        return
    def _kill_if_possible(_):
        if _.child:
            print("INTERRUPT THE CURRENT PROCESS")
            _.child = gevent.kill(_.child)
            pass
        return
    def _pub(_, content, uuid, session, model='', toolset='', **kw):
        def bg_pub():
            sess = ESP(uuid, session, funcs, _.ws(), model or _.model, _.tools)
            _.child = chat_round(sess, content, OUT_CHANNEL)
            return
        _.child = _._kill_if_possible()
        _.child = gevent.spawn(bg_pub)
        return
    pass
if __name__ == '__main__':
    Convo().main()
