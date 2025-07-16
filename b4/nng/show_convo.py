from gevent import monkey as _;_.patch_all()
import os, sys, time, json

import db_utils

from db_sync import *
#    print(load_simplified_convo(session_id))


def main():
    print("SHOW CONVOS")
    # find all sessions for a user
    
    session_id = sys.argv[1]

    while session_id.endswith(':'):
        session_id = session_id[:-1]
        pass

    for x in load_simplified_convo(session_id):
        print("X", x)
    
    #for row in get_user_sessions(uuid):
    #    print(f"Session {row['id']}: {row['content']}")
    #    pass
    pass

    
if __name__=='__main__': main()

