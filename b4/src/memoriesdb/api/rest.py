#import os, psycopg2, pgvector,
import bottle as B
from . import *


app = B.default_app()


@app.get ('/api/sessions')
def _():
    '''returns the list of sessions in descending order'''
    latest_session_id = get_latest_session(get_user_id())
    return dict(result=[latest_session_id])


@app.get ('/api/session/<session_id>')
def _(session_id):
    '''returns info about a session'''
    raise Exception('this should return the session info, '
                    'not the chat message history')


@app.post('/api/session/<session_id>')
def _(session_id):
    '''create new session'''
    result = []
    for row in load_full_session(session_id):
        j = row2dict(row)
        result.append(j)
        print(f"J{j};")
        pass
    return dict(result=result)


@app.get ('/api/history/<session_id>')
def _(session_id):
    result = []
    for row in load_full_session(session_id):
        j = row2dict(row)
        result.append(j)
        print(f"J{j};")
        pass
    return dict(result=result)


@app.get ('/api/history/')
def _():
    user_id = get_user_id()
    sess_id = get_latest_session(user_id)
    header = {'_type':'__head'}
    if B.request.query.get('full'):
        header.update({
            'user':    row2dict( get_by_id(user_id).fetchone() ),
            'session': row2dict( get_by_id(sess_id).fetchone() ),
        })
    footer = {'_type':'__foot'}
    result = []
    result.append    (f'[{json.dumps( header        )},\n')
    for row in load_full_session(user_id, sess_id):
        result.append(f' {json.dumps( row2dict(row) )},\n')
        pass
    result.append    (f' {json.dumps( footer        )}]\n')
    return result


@app.get ('/')
def _():
    return "index.html\n"
