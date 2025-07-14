from db_ll_sync import *

from logging_setup import get_logger

logger = get_logger(__name__)

def check_valid_uuid(uuid):
    conn = psycopg.connect(DSN)
    cursor = conn.cursor()
    password = os.getenv('USER_PASSWORD','el passwordo')
    
    try:        
        cursor.execute("SELECT md5(%s)=digest FROM users"
                       " WHERE users.id=%s LIMIT 1",
                       (password, uuid))
        
        if row:= cursor.fetchone():
            
            if row[-1]:
                print("PASSWORD MATCH, USER IS GOOD!")
                return uuid
            
            else:
                print("PASSWORD MISMATCH")
                raise SystemExit(6)
            
        else:
            print("user not found!", uuid)
            raise SystemExit(5)

    except psycopg.errors.InvalidTextRepresentation:
        print("WTF DUDE ARE YOU HIGH DID YOU THINK THIS WAS A VALID UUID??", uuid)
        raise SystemExit(4)

    pass

