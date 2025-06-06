#!/usr/bin/env python
'''
'''
import ollama


SYSTEM_PROMPT='''
You are a helpful assistant.
'''


class Chat:
    def __init__(_, model='mistral', system_prompt=SYSTEM_PROMPT):
        _.role = 'user'
        _.model = model
        _.messages = [dict(role='system', content=system_prompt)]
        pass

    def messages_append(_, **kw):
        return _.messages.append(kw)
    
    def chat(_, content, role=None):
        _.messages_append(role=role or _.role, content=content)    
        ret = ollama.chat(model=_.model, messages=_.messages)
        msg = ret['message']
        _.messages.append(msg)
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
            elif content:
                buffer.append(content + ' ')
                pass
            prompt = ' ' * len(prompt)
            pass
        return ''.join(buffer)
    
    def interact(_, role): 
        content = _.input(f'{role} says, "')
        return _.chat(content, role)
    
    def respond(_, content, role='assistant'):
        print(f'{role} says, "{content}"\n')
        pass
    
    def converse(_):
        while response:= _.interact(_.role):            
            _.respond(response['content'],
                      response['role'])

            pass
        pass
    pass


if __name__ == '__main__':
    Chat().converse()
