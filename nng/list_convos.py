from gevent import monkey as _;_.patch_all()
import os, sys, time, json

import db_utils

#import asyncio
#import asyncio_gevent

# make gevent/asyncio work together
#asyncio.set_event_loop_policy(asyncio_gevent.EventLoopPolicy())

from util import load_history_from_yml, load_history_from_txt

#from db_ll_sync import *
from db_sync import *

def main():
    print("LIST CONVOS")
    # find all sessions for a user
    
    uuid = sys.argv[1]

    for row in get_memories_by_uuid(uuid, " AND kind='session'"):
        print(f"Session {row['id']}: {row['content']}")
        pass
    pass

    
if __name__=='__main__': main()

