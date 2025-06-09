from api import *


init()
    
user_id = get_user_id()
print("user_id", user_id)

session_id = get_latest_session(user_id)
print("session_id", session_id)

for row in load_full_session(user_id, session_id):
    j = row2dict(row)
    print(f"J{j};")
    pass
