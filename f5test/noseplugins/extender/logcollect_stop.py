'''
Created on Sep 4, 2014

@author: jono
'''
import logging
import threading


from . import ExtendedPlugin
from .logcollect_start import MyFileHandler

LOG = logging.getLogger(__name__)
STDOUT = logging.getLogger('stdout')
CONSOLE_LOG = 'console.log'
SESSION_LOG = 'session.log'
TEST_LOG = 'test.log'
INC_TEST_ATTRIBUTES = ('author', 'rank')


class LogCollectStop(ExtendedPlugin):
    """
    Log Collector plugin. Enabled by default. Disable with ``--no-logcollect``.
    Upon a test failure this plugin iterates through each open interface and
    tries to collect troubleshooting data, like screenshots and log files.
    """
    enabled = True
    score = 1

    def _logging_leak_check(self, root_logger):
        LOG.debug("Logger leak check...ugh!")
        loggers = [('*root*', root_logger)] + root_logger.manager.loggerDict.items()
        loggers.sort(key=lambda x: x[0])
        for name, logger in loggers:
            LOG.debug("%s:%s", name, logger)
            if hasattr(logger, 'handlers'):
                for handler in logger.handlers:
                    LOG.debug(" %s", handler)

    def finalize(self, result):
        # Loose threads check
        import paramiko
        found = False
        LOG.debug("Running threads:")
        for thr in threading.enumerate():
            LOG.debug(thr)
            if isinstance(thr, paramiko.Transport):
                found = True
                LOG.warning("Thread lost: %s %s", thr, thr.sock.getpeername())
        if found:
            LOG.warning("Running paramiko.Transport threads found. Check our all "
                        "overridden tearDown, teardown_class, etc. and see that "
                        "they are correct")

        root_logger = logging.getLogger()

        # Uncomment in case of logger (or handler) leaks
        # self._logging_leak_check(root_logger)

        # Remove our filehandler from the root logger.
        for handler in root_logger.handlers[:]:
            if isinstance(handler, MyFileHandler):
                root_logger.handlers.remove(handler)
