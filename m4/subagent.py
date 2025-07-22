import os, json, websocket

WS_BASE = "ws://localhost:5002/ws"
NAME = os.getenv('NAME','llm')
IN_CHANNEL  = NAME+'-in'
OUT_CHANNEL = NAME+'-out'

class SubAgentBase:

    def connect_ws(_):
        '''this way an error doesn't leave garbage in _.ws'''
        ws = websocket.WebSocket()
        ws.connect(f'{WS_BASE}?c={IN_CHANNEL}')
        _._ws = ws
        pass

    def ws(_):
        return _._ws

    def  pub(_, params):
        return _._pub(**params)

    def _pub(_, **kw):
        raise Exception('NYI')
    
    def main(_):
        _.connect_ws()
        while 1:
            print("Waiting on socket...")
            raw = _._ws.recv()
            if not raw:
                raise EOFError
            msg = json.loads(raw)
            print("Got", (msg,), "!")
            method = msg.get('method')
            params = msg.get('params',{})
            if method=='initialize':  
                print("INIT", params)
            elif method=='pub':
                try:
                    _.pub(params)
                except:
                    import traceback
                    print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
                    traceback.print_exc()
                    print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
                    return
            else:
                print("*"*80)
                print("ERROR, BAD PACKET", msg)
                print("*"*80)
                pass
            pass
        print("EOF")
        return

    pass
