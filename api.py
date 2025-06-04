import os, psycopg2, pgvector

_conn, _cursor = None, None

def get_conn_cursor():
    if _conn:
        return _conn, _cursor
    conn = psycopg2.connect(
        host    =os.getenv('POSTGRES_HOST','localhost'),
        dbname  =os.getenv('POSTGRES_DB','memories'),
        user    =os.getenv('POSTGRES_USER','postgres'),
        password=os.getenv('POSTGRES_PASSWORD'),
    )
    cursor = conn.cursor()
    return conn, cursor

if __name__=='__main__':
    _conn, _cursor = get_conn_cursor()
    pass

def _get_memory_db_fields(cursor=_cursor):
    cursor.execute("SELECT * FROM memories LIMIT 0")
    desc = cursor.description
    ndx = dict()
    for n,column in enumerate(desc):  
        ndx[column.name] = column,n
        pass
    ndx['_public' ] = [(_.name,n) for n,_ in enumerate(desc) if not _.name.startswith('_')]
    ndx['_private'] = [(_.name,n) for n,_ in enumerate(desc) if     _.name.startswith('_')]
    return ndx

def _get_role_lookup(cursor=_cursor):
    cursor.execute("SELECT id,content FROM memories WHERE _type='role'")
    assert(cursor.rowcount > 0)

    role_lookup = dict()
    for row in cursor:
        role_lookup[row[0]] = row[1]
        role_lookup[row[1]] = row[0]
        pass
    return role_lookup

def get_latest_session(content, role='user', cursor=_cursor):
    pass

def insert_new_history(content, role='user', cursor=_cursor):
    '''
    INSERT INTO memories (_type, _parent, role, content) VALUES (
    'history', :'session_id', :'user_role_id',
    'what is 2+2?'
    ) RETURNING id as history_id \\gset
    '''
    pass

if __name__=='__main__':
    _memory_db_fields = _get_memory_db_fields()
    print("MEM DB FLDS", _memory_db_fields)

    _role_lookup = _get_role_lookup()
    print("ROLE LOOKUP TABLE", _role_lookup)
