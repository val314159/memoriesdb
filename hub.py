#!/usr/bin/env python3

from gevent import monkey as _;_.patch_all()
import os,sys,json,gevent,gevent.fileobject,websocket,geventwebsocket,time


# This makes stdin's FD non-blocking and replaces sys.stdin with
# a wrapper that is integrated into the event loop
stdin = gevent.fileobject.FileObject(sys.stdin)


def recv(ws):
    raw = ws.recv()
    if not raw:
        raise EOFError
    return json.loads(raw)


def recv2(ws):
    raw = ws.recv()
    if not raw:
        raise EOFError
    return json.loads(raw), raw


def send(ws, msg):
    return ws.send( json.dumps(msg) )


def mesg(method, **params):
    return dict(method=method, params=params)


def pub_params(ws, params, **kw):
    return send(ws, mesg('pub', **dict(params, **kw)))


def pub(ws, channel, content='', **kw):
    return send(ws, mesg('pub',
                         channel = channel,
                         content = content, **kw))


def call(ws, method, **params):
    return send(ws, dict(method=method,
                         params=params))


def add_cors_headers(headers, origin=''):
    """Add CORS headers to the response"""
    headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    headers['Access-Control-Allow-Origin' ] = origin or '*'
    headers['Access-Control-Allow-Headers'] = \
        'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'
    headers['Access-Control-Allow-Credentials'] = 'true'
    return


WS_URI = "ws://localhost:5002/ws"


def ws_connect(channels=''):
    ws = websocket.WebSocket()
    ws.connect(WS_URI+'?c='+'&c='.join(channels.split(',')))
    return ws


class HubApp:

    Channel = dict()

    def subscribe(_, ws, channels):
        rec = (hex(id(ws)), ws)
        for name in channels:
            try:
                _.Channel[name].append(rec)
            except:
                _.Channel[name] = [rec]
    
    def unsubscribe(_, ws, channels):
        rec = (hex(id(ws)), ws)
        for name in channels:
            ch = _.Channel[name]
            ch.remove(rec)
            if not ch:
                del _.Channel[name]

    def pub_raw(_, ws, channel, raw):
        for wsid2, ws2 in _.Channel.get(channel,[]):
            if ws == ws2:
                print("ITS THE SAME")
            else:
                print("SEND RAW", ws2, raw)
                ws2.send(raw)

    def pub(_, ws, msg, ch = None):
        channel = ch or  msg['params']['channel']
        raw = json.dumps(msg)
        _.pub_raw(ws, channel, raw)

    def process(_, ws):
        wsid = hex(id(ws))
        channels = request.query.getall('c')

        try:
            _.subscribe(ws, channels)
            call(ws, 'initialize',
                 wsid = wsid,
                 channels = channels)
        
            print("Waiting...")
            while raw:= ws.receive():
                print("Got", (raw,), "!")
                data = json.loads(raw)
                method = data.get('method')
                params = data.get('params',{})
                if method=='pub':
                    _.pub_raw(ws, params['channel'], raw)
                else:
                    print("BAD PACKET:", data)
                    pass
                
                time.sleep(0.2)
                print("Waiting...")
                pass
            
            time.sleep(0.2)
            
        finally:
            _.unsubscribe(ws, channels)
            pass
        
        print("BYE TO SOCKET")
        pass

    pass


from bottle import Bottle, request, response, redirect, static_file, app


class Application(HubApp, Bottle):
    pass


app = app.push(Application())


@app.route('/ws', method=['GET'])
def _():
    if ws:= request.environ.get('wsgi.websocket'):
        return request.app.process(ws)
    raise Exception('no websocket')


@app.post('/uploads')
def upload_file():
    add_cors_headers(response.headers,
                     request.headers.get('Origin'))
    try:
        os.mkdir('uploads')
    except FileExistsError:
        pass
    # TODO: if there are more than MAXIMUM_FILES files, delete the oldest
    timestamp = request.forms.get('timestamp')
    if not timestamp:
        import uuid
        timestamp = str(uuid.uuid1())
        pass
    if 'image' not in request.files:
        return {'error': 'No file part'}, 400
    image_file = request.files['image']
    if not image_file.filename:
        return {'error': 'No selected file'}, 400
    filename = f"image_{timestamp}.jpg"
    image_file.save(os.path.join('uploads', filename))
    assert 0==os.system('touch "' + os.path.join('uploads', filename+'.DUN"'))
    return {'message': f'File {filename} uploaded successfully'}


@app.get('/')
@app.get('<path:path>/')
def serve_slash(path=''):
    return static_file( path + '/index.html' )


@app.get('<path:path>')
def serve_file(path, root=os.getenv('ROOT','./public/')):
    response.headers['cache-control'] = 'no-store, must-revalidate'
    return    redirect( path + '/' ) \
        if os.path.isdir( './' + path ) else \
           static_file( path, root  )


def run(app=app, host='', port=5002):
    app.config['dns_lookups'] = False
    svr = geventwebsocket.WebSocketServer((host, port), app)
    print(f"Starting server with gevent on http://{host}:{port}")
    svr.serve_forever()
    return


if __name__ == '__main__':
    run()
