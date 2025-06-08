from gevent import monkey as _;_.patch_all()
from bottle import Bottle, request, response, redirect, static_file, app, run
import json
import time
import os
import sys
import uuid
from gevent.fileobject import FileObject
import gevent
from websocket import WebSocket
from geventwebsocket import WebSocketServer, WebSocketError
from geventwebsocket.websocket import (
    MSG_CLOSED, MSG_ALREADY_CLOSED, MSG_SOCKET_DEAD)

# This makes stdin's FD non-blocking and replaces sys.stdin with
# a wrapper that is integrated into the event loop
stdin = FileObject(sys.stdin)

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
    ws = WebSocket()
    ws.connect(WS_URI+'?c='+'&c='.join(channels.split(',')))
    return ws
