#!/usr/bin/env python3
from wsutil import *

class Application(Bottle):

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
        #print("NEW USER / PROCESS WS", wsid)
        channels = request.query.getall('c')
        #print("NEW USER / PROCESS WS", channels)

        try:
            _.subscribe(ws, channels)
            #print("INIT DATA HERE", ws)
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

    def run(_, host='', port=5002):
        _.config['dns_lookups'] = False
        svr = WebSocketServer((host, port), _)
        print(f"Starting server with gevent on http://{host}:{port}")
        svr.serve_forever()
        return

    pass


app = app.push(Application())


@app.route('/ws', method=['GET'])
def _():
    _ = request.app
    ws = request.environ.get('wsgi.websocket')
    if ws:
        return _.process(ws)
    raise Exception('no websocket')

@app.route('/api/audio/<filename>', method=['GET'])
def get_audio(filename):
    """Serve the generated audio file"""
    _ = request.app
    add_cors_headers(response.headers,
                     request.headers.get('Origin'))
    #_.add_cors_headers()
    
    #file_path = os.path.join(_.AUDIO_DIR, filename)
    file_path = os.path.join(AUDIO_DIR, filename)

    if not os.path.exists(file_path+'.DUN'):
        response.status = 404
        return "Audio file not found"

    pause = 0.125
    for n in range(5):    
        print(n, "CWD", os.path.realpath(os.curdir))
        print(n,"LOOK AT", file_path)
        if os.path.exists(file_path):
            #_.cleanup_audio(filename)
            return static_file(file_path, root='/', mimetype='audio/mpeg')
        time.sleep(pause)
        pause *= 2
        pass

    response.status = 404
    return "Audio file not found"
'''
@app.route('/api/video/<filename>', method=['GET'])
def get_video(filename):
    qq.qq.qq.qq
    """Serve the generated audio file"""
    _ = request.app
    add_cors_headers(response.headers,
                     request.headers.get('Origin'))
    #_.add_cors_headers()
    
    #file_path = os.path.join(_.AUDIO_DIR, filename)
    file_path = os.path.join(VIDEO_DIR, filename)

    print("CWD", os.path.realpath(os.curdir))
    print("LOOK AT", file_path)
    
    if os.path.exists(file_path):
        #_.cleanup_audio(filename)
        return static_file(file_path, root='/')#, mimetype='audio/mpeg')

    response.status = 404
    return "Video file not found"
'''
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
    print("QPRINT1", filename)
    print("QPRINT2", os.path.join('uploads', filename))
    image_file.save(os.path.join('uploads', filename))
    print("QPRINT3", filename)
    assert 0==os.system('touch "' + os.path.join('uploads', filename+'.DUN"'))
    return {'message': f'File {filename} uploaded successfully'}

@app.get('/')
@app.get('<path:path>/')
def _(path=''):
    print("DIR 111", path)
    return serve_file(path + '/index.html')

@app.get('<path:path>')
def serve_file(path, root=os.getenv('ROOT','./public/')):
    response.headers['cache-control'] = 'no-store, must-revalidate'
    if os.path.isdir('./' + path):
        print("SLA 000", (path, root))
        return redirect(path + '/')
    print("FIL 222", (path, root))
    if path.endswith('.mp3'):
        for n in range(25):
            print("MP3", path, root)
            pass
        pass
    return static_file(path, root)


if __name__ == '__main__': app.run()
