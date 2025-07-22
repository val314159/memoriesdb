from gevent import monkey as _;_.patch_all()
import os, sys, time, json, datetime as dt
import db_sync
from util import load_history_from_yml_raw, load_history_from_txt
def save_convo(filename):
    ts = str(dt.datetime.now(dt.UTC))[:19]
    new_title = "NewSession" + ts.replace(' ','T')
    
    if   filename.endswith('.yml'):
        history = load_history_from_yml_raw(filename)
    elif filename.endswith('.txt'):
        history = load_history_from_txt(filename)
    else:
        print("BAD FORMAT")
        raise SystemExit(1)    
    return db_sync.store_convo(history, new_title), new_title
def main():
    filename = sys.argv[1]
    convo_id, new_title = save_convo(filename)
    print(f"Saved\t{convo_id}\t{new_title}")
    if '--loadonly' not in sys.argv:
        for msg in db_sync.load_simplified_convo(convo_id):
            print("loaded", msg)
            pass
        pass
    return
if __name__=='__main__': main()

