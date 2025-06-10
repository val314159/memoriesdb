from IPython.core.magic import Magics, cell_magic, magics_class
from IPython.display import Markdown, display, display_markdown

import os, sys, time, json, websocket


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


@magics_class
class LLMMagics(Magics):

    def __init__(self, *a, **kw):
        print("INIT", (a, kw))
        __init__ = Magics.__init__
        __init__(self, *a, **kw)

        self.ws = websocket.WebSocket()
        self.ws.connect(WS_BASE + WS_ARGS)

        msg = recv(self.ws)
        print("INIT RECV", msg)

        pass
    
    @cell_magic
    def llm(self, line, cell):
        
        role = line.strip() or 'user'
        #print("ROLE", role)

        content = cell
        #print("CONTENT", content)

        pub(self.ws, CH_IN, content, role=role)       
        display(Markdown("***Waiting...***"))

        msg = recv(self.ws)
        #print("RECV", msg)

        params = msg['params']
        #print("PARAMS", params)

        output = params.get('content','[There was no content for some reason]')
        #print("OUTPUT", output)
        
        display(Markdown(output))
        return

    pass

def load_ipython_extension(ipython):
    ipython.register_magics(LLMMagics)
