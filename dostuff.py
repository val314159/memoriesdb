#!/usr/bin/env python3

import psycopg2, pgvector

DB_URI = 'postgres:pencil@localhost:5432/memories'

conn = psycopg2.connect('postgres://' + DB_URI)

def xx1(row, desc):
    d = dict((f.name,row[n])
             for n,f in enumerate(desc)
             if f.name != '_json')
    for k,v in row[-1].items():
        d[k] = v
        pass
    return d

def xx2(d):
    props = 'id _type _parent _dst _src content context_drift embeddings role'
    d1 = dict(d)
    d2 = dict()
    for prop in props.split():
        if prop in d1:
            d2[prop] = d1.pop(prop)
            pass
        pass
    d2['_json'] = d1
    return d2

def load_session(session_ids, roles):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM memories"
                   "  WHERE _type='history' AND _parent IN (%s)" %
                   repr(session_ids,)[1:-1])
    desc = cursor.description
    arr = []
    for row in cursor:
        d = {}
        for n,v in enumerate(row):
            d[desc[n].name] = v
            pass

        d['_role'] = roles[ d['role'] ]
        arr.append(d)
        pass
    return arr

def get_last_user_id():
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM memories WHERE _type='user'")
    user_id = ''
    for row in cursor:
        user_id = row[0]
        pass
    return user_id

def get_session_ids(user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT id,_src FROM memories"
                   "  WHERE _type='session' AND _parent=%s",
                   (user_id,))
    arr = []
    for row in cursor:
        arr.append(tuple(row))
        pass
    return arr

def get_session_id_chain(session_id, session_dict):
    # traverse to get all ids
    ids = []
    while session_id:
        ids.append(session_id)
        session_id = session_dict[session_id]
        pass
    return ids

def load_roles():
    cursor = conn.cursor()
    cursor.execute("SELECT id,content FROM memories WHERE _type='role'")
    desc = cursor.description
    arr = []
    for row in cursor:
        d = {}
        for n,v in enumerate(row):
            d[desc[n].name] = v
            pass
        arr.append(d)
        pass
    return arr

def index_roles():
    roles = dict()
    for role in load_roles():
        roles[role['id']] = role['content']
        roles[role['content']] = role['id']
        pass
    return roles

def mk_session_dict(session_ids):
    return dict((k,None if v==k else v) for (k,v) in session_ids)

roles = index_roles()
print("roles", roles.keys())

user_id = get_last_user_id()
print("user_id", user_id)

session_ids = get_session_ids(user_id)
print(session_ids)

session_dict = mk_session_dict(session_ids)

# get last session
session_id = session_ids[-1][0]
print("session id ", session_id)

ids = get_session_id_chain(session_id, session_dict)

for x in load_session(ids, roles):
    print(f"    {x['_role']}: {x['content']}")
    pass
