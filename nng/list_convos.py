from gevent import monkey as _;_.patch_all()
import os, sys, time, json

import db_utils

from db_sync import get_user_sessions


def main():
    print("LIST CONVOS")
    # find all sessions for a user
    
    uuid = sys.argv[1]

    for row in get_user_sessions(uuid):
        print(f"Session {row['id']}: {row['content']}")
        pass
    pass

    
if __name__=='__main__': main()

