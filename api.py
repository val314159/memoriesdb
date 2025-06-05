import os, json, psycopg2, pgvector

_dbconn, _cursor = None, None

def get_dbconn():
    global _dbconn
    if not _dbconn: _dbconn = psycopg2.connect(
            host    =os.getenv('POSTGRES_HOST','localhost'),
            dbname  =os.getenv('POSTGRES_DB',  'memories'),
            user    =os.getenv('POSTGRES_USER','postgres'),
            password=os.getenv('POSTGRES_PASSWORD'),
    )
    return _dbconn

def get_cursor(_dbconn=None):
    global _cursor 
    if not _cursor:
        dbconn = _dbconn or get_dbconn()
        _cursor = dbconn.cursor()
        pass
    return _cursor
    
def get_type_by_parent(args,
                       suffix='',
                       parms='*',
                       _cursor=None):
    cursor = _cursor or get_cursor()
    where = "WHERE _type=%s AND _parent=%s"
    sql = f"SELECT {parms} FROM memories {where} {suffix}"
    cursor.execute(sql, args)
    return cursor

def get_type          (args,
                       suffix='',
                       parms='*',
                       _cursor=None):
    cursor = _cursor or get_cursor()
    where = "WHERE _type=%s"
    sql = f"SELECT {parms} FROM memories {where} {suffix}"
    cursor.execute(sql, args)
    return cursor

def _get_memory_db_fields(_cursor=None):
    global _memory_db_fields
    cursor = _cursor or get_cursor()
    cursor.execute("SELECT * FROM memories LIMIT 0")
    desc = cursor.description
    ndx = dict()
    for n,column in enumerate(desc):  
        ndx[column.name] = column,n
        ndx[n] = column.name
        pass
    ndx['_public' ] = [(_.name,n) for n,_ in enumerate(desc) if not _.name.startswith('_')]
    ndx['_private'] = [(_.name,n) for n,_ in enumerate(desc) if     _.name.startswith('_')]
    _memory_db_fields = ndx
    return ndx

def _get_role_lookup(_cursor=None):
    global _role_lookup
    cursor = _cursor or get_cursor()
    cursor.execute("SELECT id,content FROM memories WHERE _type='role'")
    assert(cursor.rowcount > 0)
    role_lookup = dict()
    for row in cursor:
        role_lookup[row[0]] = row[1]
        role_lookup[row[1]] = row[0]
        pass
    _role_lookup = role_lookup
    return role_lookup

def insert_new_session(user_id, _src=None, _json={}, _cursor=None):
    cursor = _cursor or get_cursor()
    cursor.execute("INSERT INTO memories"
                   " (_type, _parent, _src, _json)"
                   " VALUES (%s, %s, %s, %s) RETURNING id",
                   ('session', user_id, _src, json.dumps(_json)))
    return cursor.fetchone()[0]

def insert_new_history(session_id, content, _role='user', _json={}, _cursor=None):
    cursor = _cursor or get_cursor()
    role = _role_lookup[_role]
    cursor.execute("INSERT INTO memories"
                   " (_type, _parent, role, content, _json)"
                   " VALUES (%s, %s, %s, %s, %s) RETURNING id",
                   ('history', session_id, role, content, json.dumps(_json)))
    return cursor.fetchone()[0]

def get_previous_session(session_id, _cursor=None):
    cursor = get_type          (('session',session_id),
                                suffix=" AND id=%s LIMIT 1",
                                parms='id,_src', _cursor=_cursor)
    id, src = cursor.fetchone()
    return src if id != src else None

def get_user_id(_cursor=None):
    if user_id:= os.getenv('USER_ID',''):
        return user_id
    cursor = get_type          (('user',),
                                suffix=" ORDER BY id DESC LIMIT 2",
                                _cursor=_cursor)
    assert(1==cursor.rowcount)
    return cursor.fetchone()[0]

def get_latest_session(user_id, _cursor=None):
    cursor = get_type_by_parent(('session', user_id),
                                suffix=" ORDER BY id DESC LIMIT 1",
                                parms='id,_src', _cursor=_cursor)
    return cursor.fetchone()[0]

def load_partial_session(session_id, _cursor=None):
    for row in get_type_by_parent(('history', session_id),
                                  suffix=" ORDER BY id DESC",
                                  _cursor=_cursor):
        yield list(row)
        pass
    return

def load_full_session(session_id, _cursor=None):
    while session_id:
        print("SESSION", session_id)
        for row in load_partial_session(session_id):
            yield list(row)
            pass
        session_id = get_previous_session(session_id)
        pass
    print("END SESSION")

def row2dict(row):
    j = row[-1]
    for n,v in enumerate(row):
        if v is None:
            continue

        k = _memory_db_fields[n]
        if   k == '_json':
            continue
        elif k == 'role':
            j['_' + k] = _role_lookup[v]
            pass
        j[k] = v
        pass
    return j

def init():
    print("INIT")
    _get_memory_db_fields()
    _get_role_lookup()
    pass

if __name__=='__main__':
    init()

    session_id = get_latest_session(get_user_id())
 
    _id = insert_new_history(session_id, 'new content1')
    print("_id", _id)

    _id = insert_new_history(session_id, 'new content2')
    print("_id", _id)

    _id = insert_new_history(session_id, 'new content3')
    print("_id", _id)

    _dbconn.commit()
    
    for row in load_full_session(session_id):
        j = row2dict(row)
        print(f"J{j};")
        pass
