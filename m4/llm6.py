#!/usr/bin/env python3
from gevent import monkey as _;_.patch_all()
from subagent import SubAgentBase, OUT_CHANNEL
import funcs2 as funcs

from session import EphemeralSessionProxy as ESP


class Convo(SubAgentBase):

    def __init__(_,tools=funcs.Tools, model='llama3.1'):
        _.tools, _.model, _.ws = tools, model, None
        pass

    def pub(_, params):
        sess = ESP(params['uuid'],
                   params['session'],
                   funcs, _.ws, _.model,
                   _.tools, OUT_CHANNEL)
        sess.chat_round(params['content'])
        pass
    
    pass


if __name__=='__main__':
    Convo().main()
