"""Base classes for commands.

A command is set of interactions with an entity through a single interface.
A command cannot call other commands; macros can.
"""
import hashlib
from ..base import Aliasificator, AttrDict
from ..utils.version import Version
from ..interfaces.config import ConfigInterface, ConfigNotLoaded
import logging
import time

LOG = logging.getLogger(__name__) 
LOCALCONFIG = AttrDict()


class CommandError(Exception):
    """Base exception for all exceptions raised in module config."""
    pass

class CommandTimedOut(CommandError):
    """The nose test-config plugin was not loaded."""
    def __init__(self, message, result=None):
        self.result = result
        super(CommandTimedOut, self).__init__(message)


class Command(object):

    __metaclass__ = Aliasificator
    
    def __init__(self, version=None):
        if version and not isinstance(version, Version):
            self.version = Version(version)
        else:
            self.version = version
    
    def __repr__(self):
        return "%s.%s" % (self.__module__, self.__class__.__name__)
    
    def prep(self):
        """Preparation"""
        pass

    def setup(self):
        """Core steps"""
        pass

    def run(self):
        """The main method of the Command"""
        try:
            self.prep()
            return self.setup()
        except:
            self.revert()
            LOG.error("%s", self)
            raise
        finally:
            self.cleanup()

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

        try:
            config = ConfigInterface().open()
        except ConfigNotLoaded:
            config = LOCALCONFIG
        
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
            
            config._cache.update({key:ret})
            
            #LOG.debug("cache miss :( (%s:%s)", self._key, ret)
            return ret

    def _hash(self):
        raise NotImplementedError('Must implement _hash() in superclass')

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

    def run_wait(self, condition=None, progress_cb=None, timeout=180, 
                 interval=5, stabilize=0, message=None):
        
        if not condition:
            condition = lambda x:x
        
        assert callable(condition), "The condition must be callable!"
        now = start = time.time()
        
        last_ret = ret = None
        stable = 0
        while now - start < timeout:
            good = False
            success = False
            try:
                self.prep()
                ret = self.setup()
                success = True
                if condition(ret):
                    good = True
            except Exception, e:
                LOG.debug('Error running command. (%s)', e)
                self.revert()
            finally:
                self.cleanup()
                if good:
                    LOG.debug('Criteria met (%s). Cleaning up...', ret)
                    if stable >= stabilize:
                        break
                    else:
                        if last_ret == ret:
                            LOG.debug('Criteria met and stable')
                            stable += interval
                        else:
                            LOG.debug('Criteria met but not stable')
                            stable = 0
                    last_ret = ret
                else:
                    stable = 0
                    if success:
                        if progress_cb:
                            info = progress_cb(ret)
                            if info:
                                LOG.info(info)
                        else:
                            LOG.debug('Criteria not met (%s). Sleeping %ds...', ret, 
                                      interval)
                time.sleep(interval)
                now = time.time()
        else:
            LOG.warn('Criteria not met. Giving up...')
            if message:
                raise CommandTimedOut(message, ret)
            raise CommandTimedOut('Condition not met after %d seconds.' % 
                                  timeout, ret)
        return ret
