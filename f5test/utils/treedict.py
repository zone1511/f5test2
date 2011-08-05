'''
Created on Jun 11, 2011

@author: jono
'''
def merge_dictionary(dst, src):
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
