import os, json, psycopg2, pgvector

class NotYetImplemented(Exception): pass

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
    
def generate_uuid(_cursor=None):
    cursor = _cursor or get_cursor()
    cursor.execute("SELECT uuid_generate_v1mc()")
    return cursor.fetchone()[0]

def get_type_by_parent(args,
                       suffix='',
                       parms='*',
                       _cursor=None):
    cursor = _cursor or get_cursor()
    where = "WHERE _type=%s AND _parent=%s"
    sql = f"SELECT {parms} FROM memories {where} {suffix}"
    cursor.execute(sql, args)
    return cursor

def get_type2(type1, type2,
              suffix='',
              parms='*',
              _cursor=None):
    cursor = _cursor or get_cursor()
    where = "WHERE _type IN (%s,%s)"
    sql = f"SELECT {parms} FROM memories {where} {suffix}"
    cursor.execute(sql, (type1, type2))
    return cursor

_memory_db_fields, _lookup_role = None, None

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
    ndx['_public' ] = [(_.name,n) for n,_ in enumerate(desc)
                       if not _.name.startswith('_')]
    ndx['_private'] = [(_.name,n) for n,_ in enumerate(desc)
                       if     _.name.startswith('_')]
    _memory_db_fields = ndx
    return ndx

def memory_db_fields(n):
    if _memory_db_fields:
        return _memory_db_fields[n]
    _get_memory_db_fields(get_dbconn().cursor())
    return memory_db_fields(n)

def _get_lookup_role(_cursor=None):
    global _lookup_role
    cursor = _cursor or get_cursor()
    cursor.execute("SELECT id,content FROM memories WHERE _type='role'")
    assert(cursor.rowcount > 0)
    lookup_role = dict()
    for row in cursor:
        lookup_role[row[0]] = row[1]
        lookup_role[row[1]] = row[0]
        pass
    _lookup_role = lookup_role
    return lookup_role

def lookup_role(role):
    if _lookup_role:
        return _lookup_role[role]
    _get_lookup_role()
    return lookup_role(role)
    
def insert_new_(_type, _parent, content=None, _json={}, _cursor=None):
    cursor = _cursor or get_cursor()
    _src = old_session_id
    cursor.execute("INSERT INTO memories(_type, _parent, content, _json)"
                   " VALUES (%s, %s, %s, %s) RETURNING id",
                   (_type, _parent, content, json.dumps(_json)))
    return cursor.fetchone()[0]

def _get_category_id(name, _cursor=None):
    cursor = _cursor or get_cursor()
    cursor.execute("SELECT id FROM memories"
                   " WHERE _type=%s AND content=%s",
                   ('category', name))
    return cursor.fetchone()[0]

CategoryId = None
def get_category_id(name='category', _cursor=None):
    global CategoryId
    if not CategoryId:
        CategoryId = _get_category_id('category', _cursor)
    return CategoryId

EntityId = None
def get_entity_id(_cursor=None):
    global EntityId
    if not EntityId:
        EntityId   = _get_category_id(  'entity', _cursor)
    return EntityId

RoleId = None
def get_role_id(_cursor=None):
    global RoleId
    if not RoleId:
        RoleId     = _get_category_id(    'role', _cursor)
    return RoleId


def insert_new_category(name, _json={}, _cursor=None):
    return insert_new_('category', get_category_id(_cursor), _json, _cursor)

def insert_new_role(name, _json={}, _cursor=None):
    return insert_new_('role', get_role_id(_cursor), name, _json, _cursor)

def insert_new_entity(_type, _json={}, _cursor=None):
    return insert_new_(_type, get_entity_id(_cursor), name, _json, _cursor)

def insert_fresh_session(user_id, _json={}, _cursor=None):
    cursor = _cursor or get_cursor()
    previous = generate_uuid(cursor)
    cursor.execute("INSERT INTO memories(_type, _parent, _src, _json, id)"
                   " VALUES (%s, %s, %s, %s, %s) RETURNING id",
                   ('session', user_id, previous, json.dumps(_json), _src))
    return cursor.fetchone()[0]

def insert_forkd_session(user_id, previous, _json={}, _cursor=None):
    cursor = _cursor or get_cursor()
    cursor.execute("INSERT INTO memories(_type, _parent, _src, _json)"
                   " VALUES (%s, %s, %s, %s    ) RETURNING id",
                   ('session', user_id, previous, json.dumps(_json)))
    return cursor.fetchone()[0]

def insert_new_session(user_id, previous=None, _json={}, _cursor=None):
    return insert_forkd_session(user_id, previous, _json, _cursor) \
        if old_session_id else \
           insert_fresh_session(user_id,           _json, _cursor)

def insert_new_history(session_id, content, _role='user',
                       _json={}, _cursor=None):
    cursor = _cursor or get_cursor()
    role = lookup_role(_role)
    cursor.execute("INSERT INTO memories(_type, _parent, role, content, _json)"
                   " VALUES (%s, %s, %s, %s, %s) RETURNING id",
                   ('history', session_id, role, content, json.dumps(_json)))
    ret  = cursor.fetchone()[0]
    cursor.connection.commit()
    return ret

def get_previous_session(user_id, session_id, _cursor=None):
    cursor = get_type_by_parent(('session', user_id, session_id),
                      suffix=" AND id=%s LIMIT 1",
                      parms='id,_src', _cursor=_cursor)
    id, src = cursor.fetchone()
    return src if id != src else None

def get_user_id(_cursor=None):
    if user_id:= os.getenv('USER_ID',''):
        return user_id
    cursor = get_type_by_parent(('user', get_entity_id(_cursor)),
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
        #print("   PART", row)
        yield list(row)
        pass
    return

def load_full_session(user_id, session_id, _cursor=None):
    #print("SESSION", session_id)    
    for row in get_type2('history','session',
                          suffix=" ORDER BY id DESC",
                          _cursor=_cursor):
        #print("R", row)
        if   row[1] == 'session':
            #print("SESS", row)
            session_id = row[4]
        elif row[1] == 'history':
            if row[2] == session_id:
                #print("HIST", row)
                #print("HIST", row)
                #x = list(row)
                yield list(row)
            else:
                print("hist", row)
        continue
        if   row[1] == 'session':
            print("SESS", row)
            session_id = row[4]
        elif row[1] == 'history':
            if row[2] == session_id:
                print("HIST", row)
                x = list(row)
                yield list(row)
            else:
                print("hist", row)
        else:
            raise Exception
        pass
    return
    while session_id:
        print("SESSION", session_id)
        for row in load_partial_session(session_id):
            yield list(row)
            pass
        session_id = get_previous_session(user_id, session_id)
        pass
    print("END SESSION")

def row2dict(row):
    j = row[-1]
    for n,v in enumerate(row):
        if v is None:
            continue
        k = memory_db_fields(n)
        if k == '_json':
            continue
        if k == 'role':
            j['_' + k] = lookup_role(v)
            pass
        j[k] = v
        pass
    return j

def _init():
    print(">> Initializing API...")
    _get_memory_db_fields()
    _get_lookup_role()
    get_category_id()
    get_entity_id()
    get_role_id()
    if 0:
        category_category_id()
        entity_category_id()
        role_category_id()
    pass

if __name__=='__main__':
    #_init()
    
    user_id = get_user_id()
    print("user_id", user_id)

    session_id = get_latest_session(user_id)
    print("session_id", session_id)

    _id = insert_new_history(session_id, 'new content1')
    print("_id", _id)

    _id = insert_new_history(session_id, 'new content2')
    print("_id", _id)

    _id = insert_new_history(session_id, 'new content3')
    print("_id", _id)

    _dbconn.commit()
    
    for row in load_full_session(user_id, session_id):
        j = row2dict(row)
        print(f"J{j};")
        pass
