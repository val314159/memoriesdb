from gevent import monkey as _;_.patch_all()
import os, sys, time, json

import db_utils

import asyncio
import asyncio_gevent

# make gevent/asyncio work together
asyncio.set_event_loop_policy(asyncio_gevent.EventLoopPolicy())

from util import load_history_from_yml, load_history_from_txt

from db_ll_sync import *
from db_sync import *

def store_convo(history):
    conn = psycopg.connect(DSN)
    cursor = conn.cursor()
    print("C/C", conn, cursor)
    for h in history:
        print("H", h)
        pass
    uuid = get_current_user_id()
    x = create_memory("test memory", uuid)
    print("X", x)
    #asyncio.run(db_utils.create_memory("xxx"))    
    pass

def main():
    filename = sys.argv[1]
    print("LOAD CONVO", filename)
    if   filename.endswith('.yml'):
        history = load_history_from_yml(filename)
    elif filename.endswith('.txt'):
        history = load_history_from_txt(filename)
    else:
        print("BAD FORMAT")
        raise SystemExit(1)
    store_convo(history)

if __name__=='__main__': main()
        
