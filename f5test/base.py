try:
    import unittest2 as unittest
except ImportError:
    import unittest

import sys
import re
import copy
import optparse


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
        self.port = 0
        self._priority = 10

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self.close(exc_type, exc_value, traceback)

    def __repr__(self):
        name = self.__class__.__name__
        return "<{0}: {1.username}:{1.password}@{1.address}:{1.port}>".format(name, self)

    def is_opened(self):
        return bool(self.api)

    def open(self):  # @ReservedAssignment
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
        if isinstance(default, optparse.Values):
            default = default.__dict__
        self.update(default, **kwargs)

    def __getattr__(self, n):
        try:
            return self[n]
        except KeyError:
            if n.startswith('__'):
                raise AttributeError(n)
            return None

    def __setattr__(self, n, v):
        self.update({n: v})

    def __copy__(self):
        return self.__class__(**self)

    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        result = self.__class__()
        memo[id(self)] = result
        for key, value in dict.items(self):
            dict.__setitem__(result, copy.deepcopy(key, memo),
                             copy.deepcopy(value, memo))
        return result

    def setifnone(self, key, value):
        if self.get(key) is None:
            self.update({key: value})

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
                elif isinstance(v, list):
                    d[k] = v[:]
                    for i, item in enumerate(v):
                        if isinstance(item, dict):
                            d[k][i] = AttrDict(item)
                else:
                    d[k] = v

        for arg in args:
            if hasattr(arg, 'items'):
                combine(self, arg)
        combine(self, kwargs)


class Options(AttrDict):
    pass

# Convince yaml that AttrDict is actually a dict.
try:
    from yaml.representer import Representer
    Representer.add_representer(AttrDict, Representer.represent_dict)
    Representer.add_representer(Options, Representer.represent_dict)
except ImportError:
    pass


class Aliasificator(type):
    """Adds shortcut functions at the module level for easier access to simple
    macros.

    class BrowseTo(Command):
        def __init__(self, arg='nothing'):
            self.arg = arg

        def setup(self):
            print self.arg

    >>> UI.common.browse_to('Menu | SubMenu')

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
