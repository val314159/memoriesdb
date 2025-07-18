#!/usr/bin/env python3
from gevent import monkey as _;_.patch_all()
import os
from subagent import SubAgentBase, OUT_CHANNEL
import funcs2 as funcs

from session import EphemeralSessionProxy as ESP

MODEL = os.getenv('MODEL', 'llama3.1')

class Convo(SubAgentBase):
    def __init__(_,tools=funcs.Tools, model=MODEL):
        _.tools, _.model, _.ws = tools, model, None
        pass
    def _pub(_, content, uuid, session, **kw):
        sess = ESP(uuid, session, funcs, _.ws, _.model, _.tools)
        sess.chat_round(content, OUT_CHANNEL)
        return
    pass

if __name__ == '__main__':
    Convo().main()
