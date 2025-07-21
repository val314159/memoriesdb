from gevent import monkey as _;_.patch_all()
import os, sys, time, json, datetime as dt

import db_utils

from util import load_history_from_yml_raw, load_history_from_txt

import db_sync as db

def main():
    ts = str(dt.datetime.now(dt.UTC))[:19]
    
    filename = sys.argv[1]
    
    if   filename.endswith('.yml'):
        history = load_history_from_yml_raw(filename)
    elif filename.endswith('.txt'):
        history = load_history_from_txt(filename)
    else:
        print("BAD FORMAT")
        raise SystemExit(1)

    if '--loadonly' not in sys.argv:
        print('='*80)
        pass
    
    new_title = "NewSession" + ts.replace(' ','T')
    convo_id = db.store_convo(history, new_title)
    print(f"Saved\t{convo_id}\t{new_title}")
    
    if '--loadonly' not in sys.argv:
        for msg in db.load_simplified_convo(convo_id):
            print("loaded", msg)
            pass
        pass
    pass

if __name__=='__main__': main()

