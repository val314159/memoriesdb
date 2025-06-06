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


class PS:

    channels = {}

    def __init__(_, ws):
        _.ws = ws
        _.wsid = hex(id(ws))[:2]
        try:
            _.adduser()
            _.hi_user()
            _.loop()
        finally:
            _.deluser()
    
    def loop(_):
        while msg:= ws.receive():
            for ws2 in _.channels.get(ws.receive(), []):
                ws2.send(msg)
    
    def send(_, method, **params):
        return ws.send(json.dumps(
            dict(method=method, params=params)))
 
    def hi_user(_):
        ws.send('welcome', ws=wsid)

    def adduser(_):
        for ch in _.channels.split('/'):
            _.channels.setdefault(ch,[])
            _.channels[ch].append(ws)
            _.channels[wsid] = ws

    def deluser(_):
        for ch in _.channels.split('/'):
            del   _.channels[ch]
            del   _.channels[wsid]


