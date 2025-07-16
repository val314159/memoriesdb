from gevent import monkey as _;_.patch_all()
import os, sys, time, json

import db_utils

from db_sync import get_last_session, get_current_user_id, load_simplified_convo


def main():
    print("SHOW CONVOS")
    # find all sessions for a user

    try:
        uuid = sys.argv[2] 
    except IndexError:
        uuid = get_current_user_id()
        pass

    try:
        session_id = sys.argv[1]
        while session_id.endswith(':'):
            session_id = session_id[:-1]
            pass
    except IndexError:
        row = get_last_session(uuid)
        print("ROW:", row)
        session_id = str(row['id'])
        pass

    for x in load_simplified_convo(session_id):
        print("  -", x)
    
    pass

    
if __name__=='__main__': main()

