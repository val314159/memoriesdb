#!/usr/bin/env python3
from gevent import monkey as _;_.patch_all()
import os, gevent, gevent.queue
from subagent import SubAgentBase, OUT_CHANNEL
import funcs2 as funcs
from session import EphemeralSessionProxy as ESP, chat_round
class Convo(SubAgentBase):
    def __init__(_,tools=funcs.Tools, model=os.getenv('MODEL', 'llama3.1')):
        _.tools, _.model = tools, model
        pass
    def _pub(_, content, uuid, session, model='', toolset='', **kw):
        sess = ESP(uuid, session, funcs, _.ws(), model or _.model, _.tools)
        chat_round(sess, content, OUT_CHANNEL)
        return
    pass
if __name__ == '__main__':
    Convo().main()
