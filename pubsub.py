import json, bottle as B
#from memoriesdb.api import *


app = B.default_app()


Channels = {}


@app.get ('/ps/<channels:path>')
def _(channels):
    try:
        ws = B.request.environ['wsgi.websocket']
    except:
        raise B.abort(404)

    wsid = hex(id(ws))[:2]
    
    def send(method, **params):
        return ws.send(json.dumps(
            dict(method=method, params=params)))
 
    def adduser():
        for ch in channels.split('/'):
            Channels.setdefault(ch,[])
            Channels[ch].append(ws)
            Channels[wsid] = ws
            pass
        pass

    def deluser():
        for ch in channels.split('/'):
            del Channels[ch]
            del Channels[wsid]
            pass
        pass

    def hi_user():
        send('welcome', ws=wsid)
        pass
    
    hi_user()
    adduser()
    while msg:= ws.receive():
        for ws2 in Channels.get(ws.receive(), []):
            ws2.send(msg)
            pass
        pass        
    deluser()

