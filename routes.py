import os, psycopg2, pgvector, bottle as B
from memoriesdb.api import *


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
    session_id = get_latest_session(user_id)
    header = {}
    footer = {}
    result = []
    count = 0
    header['user_id'] = user_id
    header['session_id'] = session_id
    result.append        (f'[{json.dumps( header        )},\n')
    try:
        for row in load_full_session(user_id, session_id):
            result.append(f' {json.dumps( row2dict(row) )},\n')
            count += 1
            pass
        footer['count'] = count
        result.append    (f' {json.dumps( footer        )}]\n')
        return result
    except:
        return ["ok"]


@app.get ('/')
def _():
    return "index.html\n"
