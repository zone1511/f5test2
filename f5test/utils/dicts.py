'''
Created on Jun 11, 2011

@author: jono
'''
import types

def merge_dict(dst, src):
    stack = [(dst, src)]
    while stack:
        current_dst, current_src = stack.pop()
        for key in current_src:
            if key not in current_dst:
                if isinstance(current_src[key], dict):
                    if current_dst.get(key):
                        del current_dst[key]
                    b = current_dst.makeBranch(key)
                    b.update(current_src[key])
                else:
                    current_dst[key] = current_src[key]
            else:
                if isinstance(current_src[key], dict) and isinstance(current_dst[key], dict) :
                    stack.append((current_dst[key], current_src[key]))
                else:
                    if isinstance(current_src[key], dict):
                        if current_dst.get(key):
                            del current_dst[key]
                        b = current_dst.makeBranch(key)
                        b.update(current_src[key])
                    else:
                        current_dst[key] = current_src[key]
    return dst

def invert_dict(src, keys=None):
    """
    Reverts a dict of key:value into value:key.
    
    >>> src = dict(key1='val1', key2=['val2', 'val3'], key3='val3')
    >>> trans = dict(val3='gaga', val2='gaga')
    >>> invert_dict(src)
    {'val3': set(['key3', 'key2']), 'val2': set(['key2']), 'val1': set(['key1'])}
    >>> invert_dict(src, trans)
    {'val1': set(['key1']), 'gaga': set(['key3', 'key2'])}

    @param src: Source dict
    @type src: dict
    @param keys: Key transform dict
    @type keys: dict
    """
    outdict = {}
    if keys is None:
        keys = {}

    for k,lst in src.items():
        if type(lst) is types.StringType:
            lst = lst.split()
        for entry in lst:
            entry = keys.get(entry, entry)
            outdict.setdefault(entry, set())
            outdict[entry].add(k)

    return outdict
