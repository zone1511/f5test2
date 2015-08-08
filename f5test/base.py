try:
    import unittest2 as unittest
except ImportError:
    import unittest

from collections import OrderedDict
import copy
import optparse
import re
import sys
import warnings
from f5test.noseplugins.extender.known_issue import KnownIssueTest

# Monkey patch for Python 2.7.9 CERT_REQUIRED enforcing.
# TODO: Update HTTPS clients to pass CERT_NONE explicitly, then remove this.
import ssl
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context


def enum(*args, **kwargs):
    enums = dict(zip(args, args), **kwargs)
    return type('Enum', (), enums)


def main(*args, **kwargs):
    import nose
    from f5test.noseplugins.extender.logcollect_start import LogCollect
    from f5test.noseplugins.testconfig import TestConfig

    return nose.main(addplugins=[TestConfig(), LogCollect()], defaultTest=sys.argv[0])


class TestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestCase, self).__init__(*args, **kwargs)
        self.error_context = None

    def has_failed(self):
        """Returns true if the current test has failed.
        To be used in tearDown()"""
        for test, _ in self._resultForDoCleanups.errors + self._resultForDoCleanups.failures:
            if test.id() == self.id():
                return True
        return False

    def id(self):
        ret = super(TestCase, self).id()
        if self.error_context:
            return "%s:%s" % (ret, self.error_context)
        return ret

    def fail_ki(self, message):
        raise KnownIssueTest(message)

    def run(self, result=None):
        """This is the original method from unittest.TestCase modified to
        execute tearDown always (i.e. even when an exception occurs in the setUp)

        - Added error_context tracking.
        - Changed id() to generate different signatures for when the test
        errored in setUp or tearDown.
        """
        orig_result = result
        if result is None:
            result = self.defaultTestResult()
            startTestRun = getattr(result, 'startTestRun', None)
            if startTestRun is not None:
                startTestRun()

        self._resultForDoCleanups = result
        result.startTest(self)

        testMethod = getattr(self, self._testMethodName)
        if (getattr(self.__class__, "__unittest_skip__", False) or
                getattr(testMethod, "__unittest_skip__", False)):
            # If the class or method was skipped.
            try:
                skip_why = (getattr(self.__class__, '__unittest_skip_why__', '')
                            or getattr(testMethod, '__unittest_skip_why__', ''))
                self._addSkip(result, skip_why)
            finally:
                result.stopTest(self)
            return
        try:
            success = False
            try:
                self.setUp()
            except unittest.case.SkipTest as e:
                self._addSkip(result, str(e))
            except KeyboardInterrupt:
                raise
            except:
                self.error_context = 'setup'
                result.addError(self, sys.exc_info())
            else:
                try:
                    testMethod()
                except KeyboardInterrupt:
                    raise
                except self.failureException:
                    result.addFailure(self, sys.exc_info())
                except unittest.case._ExpectedFailure as e:
                    addExpectedFailure = getattr(result, 'addExpectedFailure', None)
                    if addExpectedFailure is not None:
                        addExpectedFailure(self, e.exc_info)
                    else:
                        warnings.warn("TestResult has no addExpectedFailure method, reporting as passes",
                                      RuntimeWarning)
                        result.addSuccess(self)
                except unittest.case._UnexpectedSuccess:
                    addUnexpectedSuccess = getattr(result, 'addUnexpectedSuccess', None)
                    if addUnexpectedSuccess is not None:
                        addUnexpectedSuccess(self)
                    else:
                        warnings.warn("TestResult has no addUnexpectedSuccess method, reporting as failures",
                                      RuntimeWarning)
                        result.addFailure(self, sys.exc_info())
                except unittest.case.SkipTest as e:
                    self._addSkip(result, str(e))
                except:
                    result.addError(self, sys.exc_info())
                else:
                    success = True

            try:
                self.tearDown()
            except KeyboardInterrupt:
                raise
            except:
                self.error_context = 'teardown'
                result.addError(self, sys.exc_info())
                success = False

            cleanUpSuccess = self.doCleanups()
            success = success and cleanUpSuccess
            if success:
                result.addSuccess(self)
        finally:
            result.stopTest(self)
            if orig_result is None:
                stopTestRun = getattr(result, 'stopTestRun', None)
                if stopTestRun is not None:
                    stopTestRun()


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

                if isinstance(v, AttrDict):
                    d[k] = v
                # This will convert any dict or OrderedDict instance into AttrDict
                elif type(v) in (dict, OrderedDict):
                    if not isinstance(d[k], dict):
                        d[k] = AttrDict()
                    combine(d[k], v)
                elif isinstance(v, list):
                    d[k] = type(v)(v)
                    for i, item in enumerate(v):
                        if isinstance(item, dict):
                            d[k][i] = AttrDict(item)
                else:
                    d[k] = v

        for arg in args:
            if hasattr(arg, 'items'):
                combine(self, arg)
        combine(self, kwargs)

Options = AttrDict

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
        alias = re.sub("([A-Z])", lambda mo: (mo.start() > 0 and '_' or '') +
                       mo.group(1).lower(), name)

        # Create the class so that we can call its __init__ in the stub()
        klass = super(Aliasificator, cls).__new__(cls, name, bases, attrs)

        def stub(*args, **kwargs):
            return klass(*args, **kwargs).run()

        # Add the shortcut function to the module
        setattr(module, alias, stub)

        return klass


class Kind(object):
    SEPARATOR = ':'

    def __init__(self, kind=None):
        if isinstance(kind, Kind):
            self.bits = []
            self.bits[:] = kind.bits
        else:
            self.bits = kind.strip().lower().split(Kind.SEPARATOR) if kind else []

    def __len__(self):
        return len(self.bits)

    def __repr__(self):
        name = self.__class__.__name__
        return "<{0}: {1}>".format(name, str(self) or '*any*')

    def __str__(self):
        return ':'.join(self.bits)

    def __abs__(self):
        if not self.bits:
            raise ValueError('Unable to determine the absolute value.')
        return Kind(self.bits[0])

    def __eq__(self, other):
        if not isinstance(other, Kind):
            other = Kind(other)

        # Any special case
        if not self.bits:
            return True

        return self.bits[:len(other)] == other.bits

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        raise NotImplementedError('Operation not permitted.')

    def __gt__(self, other):
        raise NotImplementedError('Operation not permitted.')
