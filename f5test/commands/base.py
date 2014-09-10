"""Base classes for commands.

A command is set of interactions with an entity through a single interface.
A command cannot call other commands; macros can.
"""
import hashlib
from ..base import Aliasificator
from ..utils.version import Version
from ..utils.wait import CallableWait
from ..interfaces.config import ConfigInterface
from ..interfaces.testcase import ContextHelper
import logging
import threading

LOG = logging.getLogger(__name__)


class CommandError(Exception):
    """Base exception for all exceptions raised in module config."""
    pass


class CommandTimedOut(CommandError):
    """The Command timed out."""
    def __init__(self, message, result=None):
        self.result = result
        super(CommandTimedOut, self).__init__(message)


class Command(threading.Thread):

    __metaclass__ = Aliasificator

    def __init__(self, version=None):
        if version and not isinstance(version, Version):
            self.version = Version(version)
        else:
            self.version = version
        self.result = None
        super(Command, self).__init__()

    def __repr__(self):
        return "%s.%s" % (self.__module__, self.__class__.__name__)

    def prep(self):
        """Preparation"""
        self.context = ContextHelper(__file__)

    def setup(self):
        """Core steps"""
        self.context.teardown()

    def run(self):
        """The main method of the Command"""
        LOG.debug("In command: %s", self)
        try:
            self.prep()
            self.result = self.setup()
            return self.result
        except Exception, e:
            self.revert()
            LOG.error("%s %r", self, e)
            raise
        finally:
            self.cleanup()

    def join(self, *args, **kwargs):
        super(Command, self).join(*args, **kwargs)
        return self.result

    def run_wait(self, *args, **kwargs):
        raise NotImplementedError('Not a waitable command.')

    def revert(self):
        """In case of a failure, revert prep/setup steps"""
        pass

    def cleanup(self):
        """Always called at the end"""
        pass


class CachedCommand(Command):
    """Base class for cached Commands.

    The result of a cached command will be retrieved from the cache.
    The optional flag '_no_cache' can be set to signal that the result cache
    for this command should be cleared.

    @param _no_cache: if set the result of the command will always be stored in
                    the cache.
    @type _no_cache: bool
    """
    def __init__(self, _no_cache=False, *args, **kwargs):
        super(CachedCommand, self).__init__(*args, **kwargs)
        self._no_cache = _no_cache

    def run(self, *args, **kwargs):

        LOG.debug('CachedCommand KEY: %s', self)
        key = hashlib.md5(str(self)).hexdigest()

        config = ConfigInterface().open()

        if not config._cache:
            config._cache = {}

        if self._no_cache:
            config._cache.pop(key, None)
            ret = None
        else:
            ret = config._cache.get(key)

        if ret:
            LOG.debug("CachedCommand hit: %s", ret)
            return ret
        else:
            ret = super(CachedCommand, self).run(*args, **kwargs)

            config._cache.update({key: ret})

            # LOG.debug("cache miss :( (%s:%s)", self._key, ret)
            return ret

    def _hash(self):
        raise NotImplementedError('Must implement _hash() in superclass')


class CommandWait(CallableWait):

    def __init__(self, command, *args, **kwargs):
        self._command = command
        return super(CommandWait, self).__init__(None, *args, **kwargs)

    def function(self, *args, **kwargs):
        self._command.prep()
        self._result = self._command.setup(*args, **kwargs)

    def test_error(self, exc_type, exc_value, exc_traceback):
        self._command.revert()
        return super(CommandWait, self).test_error(exc_type, exc_value, exc_traceback)

    def cleanup(self):
        self._command.cleanup()
        return super(CommandWait, self).cleanup()


class WaitableCommand(Command):
    """Helper class for Commands that provides a run_wait method. This method
    won't return unless the condition is met. The Command's prep, revert and
    cleanup methods will still be executed accordingly.

    @param condition: a function that takes a command return value as parameter
                      and returns a boolean. True means condition is satisfied
                      False means keep looping.
    @type condition: callable
    @param retries: how many times to loop
    @type retries: int
    @param interval: seconds to sleep after every failed iteration
    @type interval: int
    @param stabilize: seconds to wait for the value to stabilize
    @type stabilize: int
    """

    def run_wait(self, *args, **kwargs):
        LOG.debug("In command: %s", self)
        w = CommandWait(self, *args, **kwargs)
        return w.run()
