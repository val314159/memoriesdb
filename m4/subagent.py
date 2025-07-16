import os, json, websocket


NAME = os.getenv('NAME','llm')
IN_CHANNEL  = NAME+'-in'
OUT_CHANNEL = NAME+'-out'
WS_BASE = "ws://localhost:5002/ws"


class SubAgentBase:

    def connect_ws(_):
        '''this way an error doesn't leave garbage in _.ws'''
        ws = websocket.WebSocket()
        ws.connect(f'{WS_BASE}?c={IN_CHANNEL}')
        _.ws = ws
        pass

    def pub(_, params):
        raise Exception('NYI')
    
    def main(_):
        _.connect_ws()
        while 1:
            print("Waiting on socket...")
            raw = _.ws.recv()
            if not raw:
                raise EOFError
            msg = json.loads(raw)
            print("Got", (msg,), "!")
            method = msg.get('method')
            params = msg.get('params',{})
            if method=='initialize':  
                print("INIT", params)
            elif method=='pub':
                _.pub(params)
            else:
                print("*"*80)
                print("ERROR, BAD PACKET", msg)
                print("*"*80)
                pass
            pass
        print("EOF")
        return

    pass
