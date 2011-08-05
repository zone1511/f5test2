try:
    import unittest2 as unittest
except ImportError:
    import unittest

import sys
import re


def main(*args, **kwargs):
    import nose
    from f5test.noseplugins.logcollect import LogCollect
    from f5test.noseplugins.testconfig import TestConfig

    return nose.main(addplugins=[TestConfig(), LogCollect()], defaultTest=sys.argv[0]) 


class TestCase(unittest.TestCase):
    pass


class Interface(object):

    def __init__(self, *args, **kwargs):
        self.api = None
        self.address = None
        self.username = None
        self.password = None

    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        return self.close(exc_type, exc_value, traceback)
    
    def is_opened(self):
        return bool(self.api)

    def open(self):
        pass

    def close(self, *args, **kwargs):
        self.api = None

class AttrDict(dict):
    """
        A dict accessible by attributes.
        
        >>> ad = AttrDict()
        >>> ad.flags=dict(cat1={})
        >>> ad.flags.cat1.flag1 = 1
        >>> ad.flags.cat1['flag 2'] = 2
        >>> ad.flags
        {'cat1': {'flag 2': 2, 'flag1': 1}}
    """

    def __init__(self, default=None, **kwargs):
        self.update(default, **kwargs)

    #def __new__(cls, *args, **kwargs):
        #self = dict.__new__(cls, *args, **kwargs)
        #print cls.__dict__
        #self.update(cls.__dict__, **kwargs)
        #return self

    def __getattr__(self, n):
        try:
            return self[n]
        except KeyError:
            return None

    @property
    def __dict__(self):
        return self

    def __setattr__(self, n, v):
        self.update({n:v})

    def update(self, *args, **kwargs):
        """Takes similar args as dict.update() and converts them to AttrDict.
        
        No recursion check is made!
        """
        def combine(d, n):

            for k, v in n.items():
                d.setdefault(k, AttrDict())
                
                if isinstance(v, dict):
                    if not isinstance(d[k], dict):
                        d[k] = AttrDict()
                    combine(d[k], v)
                else:
                    d[k] = v

        for arg in args:
            if hasattr(arg, 'items'):
                combine(self, arg)
        combine(self, kwargs)


class Options(AttrDict):
    pass


class Aliasificator(type):
    """Adds shortcut functions at the module level for easier access to simple
    macros.
    
    class BrowseTo(Command):
        def __init__(self, arg='nothing'):
            self.arg = arg
        
        def setup(self):
            print self.arg
    
    >>> <module>.browse_to('something')
    something
    
    """
    def __new__(cls, name, bases, attrs):
        module = sys.modules[attrs['__module__']]
        
        # Turn NamesLikeThis into names_like_this
        alias = re.sub("([A-Z])", lambda mo: (mo.start() > 0 and '_' or '') + \
                                              mo.group(1).lower(), name)

        # Create the class so that we can call its __init__ in the stub()
        klass = super(Aliasificator, cls).__new__(cls, name, bases, attrs)

        def stub(*args, **kwargs):
            return klass(*args, **kwargs).run()

        # Add the shortcut function to the module
        setattr(module, alias, stub)

        return klass
