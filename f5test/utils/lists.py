'''
Created on May 5, 2011

@author: jono
'''
def collapse_lists(items):
    """Collapses a list of dictionaries into a dictionary with list values
    
    >>> collapse_lists([{'a': 1}, {'a': 2}])
    {'a': [1, 2]}
    """
    if not items:
        return {}
    result = {}
    for item in items:
        for key, value in item.items():
            if not result.has_key(key):
                result[key] = []
            result[key].append(value)
    return result
