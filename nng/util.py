
import yaml


def start_history_to_yml(filename='out.yml', **kw):
    with open(filename, 'a') as f:
        f.write('---\n')
        yaml.safe_dump(kw, f)
        pass
    pass


def fork_history_to_yml(filename='in.yml', **kw):

    fileroot = filename[:-3]

    fork1 = dict(k)
    fork1['forked_from'] = fileroot
    fork1['filename'] = f'{fileroot}1.yml'
    start_history_to_yml(fork1['filename'])

    fork2 = dict(k)
    fork2['forked_from'] = fileroot
    fork2['filename'] = f'{fileroot}2.yml'
    start_history_to_yml(fork2['filename'])

    return


def load_history_from_txt(filename='chat.txt'):
    
    with open(filename) as f:
        
        return [dict(system='\n'.join( f.readlines() ))]


def load_history_from_yml(filename='chat.yml'):
    
    with open(filename) as f:

        for n,m in enumerate(yaml.safe_load_all(f)):
        
            assert(type(m)==dict)

            assert( len(m)>=1 )
        
            if n == 0:
                
                m['kind'] = 'session'

                yield m
                continue
        
            for k in m:
            
                m['role'] = k
                m['content'] = m.pop(k)
                m['kind'] = 'history'
            
                yield m                
                break
