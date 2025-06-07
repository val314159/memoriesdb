#!/usr/bin/env python
'''
To run this, do:

```
uv sync
PYTHONPATH=. uv run examples/chat_ollama.py
```
'''
import dotenv
import ollama
import api
from api import insert_new_history


USER = 'userx'
ASSISTANT = 'assistantx'
SYSTEM = 'systemx'

SYSTEM_PROMPT='''
You are a helpful assistant.
'''



dotenv.load_dotenv()



class Chat:

    def insert_new_history(_, content, role):
        _.messages.append( dict(role=role, content=content) )
        return insert_new_history(_.session_id, content, role)

    def __init__(_,
                 session_id,
                 model='mistral',
                 system_prompt=SYSTEM_PROMPT):
        _.session_id = session_id
        _.model = model
        _.messages = []
        _.load_session(session_id)
        pass

    def load_session(_, session_id):
        session = list(load_full_session(user_id, session_id))
        messages = []
        for jrow in (row2dict(row) for row in session):
            messages.insert(0, dict(
                content = jrow['content'],
                role    = jrow['_role']))
            pass
        _.messages = messages
        pass
    
    def chat(_, content, role='user'):      
        _.insert_new_history(content, role)
        ret = ollama.chat(model=_.model, messages=_.messages)
        msg = ret['message']
        _.insert_new_history(msg['content'], msg['role'])
        return msg
    

    def input(_, prompt):
        buffer = []
        while 1:
            content = input(prompt)
            if   content.startswith('//'):
                role = content[1:].strip()
            elif content.startswith('/'):
                print(">> Error!  Bad command!")
            elif content.endswith('"'):
                buffer.append(content[:-1])
                break
            elif content.endswith('\x1b'):
                buffer.append(content[:-1])
                print('"')
                break
            elif content:
                buffer.append(content + ' ')
                pass
            prompt = ' ' * len(prompt)
            pass
        return ''.join(buffer)

    
    def interact(_, role='user'): 
        content = _.input(f'{role} says, "')
        return _.chat(content, role)

    
    def respond(_, content, role='assistant'):
        print(f'{role} says, "{content}"\n')
        pass

    
    def converse(_):
        while response:= _.interact():
            _.respond(response['content'],
                      response['role'])

            
    def respond(_, response):
        content = response['content']
        role = response['role']
        print(f'{role} says, "{content}"\n')
        pass

    
    def converse(_):
        while response:= _.interact():
            _.respond(response)
            pass
        pass

    
    pass # end class Chat:



if __name__ == '__main__':

    from api import *

    api._init()
    
    user_id = get_user_id()
    print("user_id", user_id)

    session_id = get_latest_session(user_id)
    print("session_id", session_id)

    Chat(session_id).converse()
