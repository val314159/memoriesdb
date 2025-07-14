from gevent import monkey as _;_.patch_all()
import os, sys, time, json

import db_utils

from util import load_history_from_yml_raw, load_history_from_txt

from db_ll_sync import *
from db_sync import *

def load_simplified_convo(convo_id):
    return simplify_convo( load_convo(convo_id) )
    
def simplify_convo(convo):
    """
    turns a complex array of dicts
    into the minumum we need to send to the context window
    """
    for msg in convo:
        kind = msg.get('kind')
        if kind == 'history':
            #print("MESSAGE")
            #print("H", msg)
            yield dict(role=msg['role'],
                       content=msg['content'])
        elif kind == 'session':
            #print("SESSION")
            pass
        else:
            NO_WAY
        pass
    pass

def load_convo(suid):
    #print("LOAD CONVO", suid)
    convo = []

    session = get_memory_by_id(suid)
    #print("SESSION", session)
    #print("SESSION", session['id'])
    yield session

    suid = session['id']

    for targets_edge in get_edges_by_target(suid):
        #print("TARGET EDGE", targets_edge)
        source_id = targets_edge['source_id']
        vertex = get_memory_by_id(source_id)
        #print("V", vertex)
        yield vertex
        pass

    pass

def store_convo(history):
    uuid = get_current_user_id()
    suid = create_memory("new session", uuid, kind='session')    
    for h in history:
        h['user_id'] = uuid
        muid = create_memory(**h)
        euid = create_memory_edge(muid, suid, 'belongsto')
        pass
    return suid

def main():
    
    filename = sys.argv[1]
    
    if   filename.endswith('.yml'):
        history = load_history_from_yml_raw(filename)
    elif filename.endswith('.txt'):
        history = load_history_from_txt(filename)
    else:
        print("BAD FORMAT")
        raise SystemExit(1)

    convo_id = store_convo(history)
    
    for msg in load_simplified_convo(convo_id):
        print("loaded", msg)
        pass
    pass

if __name__=='__main__': main()
        
