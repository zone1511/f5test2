'''
Created on Sep 4, 2014

@author: jono
'''
"""
This plugin collects logs from all devices used during a failed/errored test.
"""
import base64
import codecs
from inspect import ismodule, isclass
import logging
import os
import sys
import threading
import traceback

from nose.case import Test
from nose.plugins import logcapture
from nose.plugins.base import Plugin
from nose.plugins.skip import SkipTest
from nose.util import safe_str
import yaml

from . import ExtendedPlugin


LOG = logging.getLogger(__name__)
STDOUT = logging.getLogger('stdout')
CONSOLE_LOG = 'console.log'
SESSION_LOG = 'session.log'
TEST_LOG = 'test.log'
INC_TEST_ATTRIBUTES = ('author', 'rank')


class DummyPlugin(Plugin):
    def options(self, parser, env):
        pass
logcapture.LogCapture = DummyPlugin


class MyFileHandler(logging.FileHandler):

    def __init__(self, filename, mode='a', encoding=None, delay=0, filters=None):
        super(MyFileHandler, self).__init__(filename, mode, encoding, delay)
        self.filterset = logcapture.FilterSet(filters or [])

    def filter(self, record):
        if self.filterset.allow(record.name):
            return super(MyFileHandler, self).filter(record)


class LoggingProxy(object):
    """Forward file object to :class:`logging.Logger` instance.

    :param logger: The :class:`logging.Logger` instance to forward to.
    :param loglevel: Loglevel to use when writing messages.

    """
    closed = False
    loglevel = logging.INFO
    _thread = threading.local()

    def __init__(self, logger, loglevel=None):
        self.logger = logger
        self.loglevel = loglevel or self.logger.level or self.loglevel
        self.buffer = []

    def write(self, data):
        self.buffer.append(data)

    def writeln(self, arg=None):
        if arg:
            self.write(arg)
        data = ''.join(self.buffer)
        self.logger.log(self.loglevel, data)
        self.buffer[:] = []

    def writelines(self, sequence):
        """`writelines(sequence_of_strings) -> None`.

        Write the strings to the file.

        The sequence can be any iterable object producing strings.
        This is equivalent to calling :meth:`write` for each string.

        """
        for part in sequence:
            self.write(part)

    def flush(self):
        """This object is not buffered so any :meth:`flush` requests
        are ignored."""
        pass

    def close(self):
        """When the object is closed, no write requests are forwarded to
        the logging object anymore."""
        self.closed = True

    def isatty(self):
        """Always returns :const:`False`. Just here for file support."""
        return False

    def fileno(self):
        return None


class LogCollect(ExtendedPlugin):
    """
    Log Collector plugin. Enabled by default. Disable with ``--no-logcollect``.
    Upon a test failure this plugin iterates through each open interface and
    tries to collect troubleshooting data, like screenshots and log files.
    """
    enabled = True
    score = 540
    logformat = '%(asctime)s - %(levelname)8s [%(threadName)s] %(name)s:%(lineno)d - %(message)s'
    env_opt = 'NOSE_NOLOGCAPTURE'
    logdatefmt = None
    clear = False
    filters = []

    def options(self, parser, env):
        """Register commandline options.
        """
        parser.add_option('--console-redirect', action='store_true',
                          default=False,
                          help="Enable redirection of console output to a console.log.")
        parser.add_option('--no-logcollect', action='store_true',
                          dest='no_logcollect', default=False,
                          help="Disable LogCollect.")

    def configure(self, options, conf):
        """
        Configure plugin. Skip plugin is enabled by default.
        """
        from ...interfaces.testcase import ContextHelper
        import f5test.commands.ui as UI
        import f5test.commands.shell.ssh as SSH
        self.UI = UI
        self.SSH = SSH

        if not self.can_configure:
            return
        self.conf = conf
        self.enabled = False if getattr(options, 'no_logcollect', False) else True

        self.context = ContextHelper(self.name)
        self.logformat = options.format or self.logformat
        self.logdatefmt = options.datefmt or self.logdatefmt
        self.clear = options.get('clear') or self.clear
        self.loglevel = options.level or 'NOTSET'
        if options.filters:
            self.filters = options.filters

    def _get_session_dir(self):
        cfgifc = self.context.get_config()
        path = cfgifc.get_session().path

        if path and not os.path.exists(path):
            oldumask = os.umask(0)
            os.makedirs(path)
            os.umask(oldumask)

        return path

    def setOutputStream(self, stream):
        if not self.conf.options.console_redirect:
            return

        logger = logging.getLogger('_console_')
        logger.disabled = False

        log_dir = self._get_session_dir()
        console_filename = os.path.join(log_dir, CONSOLE_LOG)

        logformat = '%(asctime)s - %(message)s'
        fmt = logging.Formatter(logformat, self.logdatefmt)
        handler = logging.FileHandler(console_filename)
        handler.setFormatter(fmt)

        for x in logger.handlers:
            logger.removeHandler(x)
        logger.addHandler(handler)

        proxy = LoggingProxy(logger)
        return proxy

    def setupLoghandler(self):
        # setup our handler with root logger
        root_logger = logging.getLogger()
        if self.clear:
            if hasattr(root_logger, "handlers"):
                for handler in root_logger.handlers:
                    root_logger.removeHandler(handler)
            for logger in logging.Logger.manager.loggerDict.values():  # @UndefinedVariable
                if hasattr(logger, "handlers"):
                    for handler in logger.handlers:
                        logger.removeHandler(handler)
        # make sure there isn't one already
        # you can't simply use "if self.handler not in root_logger.handlers"
        # since at least in unit tests this doesn't work --
        # LogCapture() is instantiated for each test case while root_logger
        # is module global
        # so we always add new MyMemoryHandler instance
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logcapture.MyMemoryHandler):
                root_logger.handlers.remove(handler)
        root_logger.addHandler(self.handler)
        # to make sure everything gets captured
        loglevel = getattr(self, "loglevel") or "NOTSET"
        root_logger.setLevel(getattr(logging, loglevel))

    def formatLogRecords(self):
        return map(safe_str, self.handler.buffer)

    def start(self):
        self.handler = logcapture.MyMemoryHandler(self.logformat, self.logdatefmt,
                                                  self.filters)
        self.setupLoghandler()

    def begin(self):
        # setup our handler with root logger
        cfgifc = self.context.get_config()
        self.start()
        root_logger = logging.getLogger()

        log_dir = self._get_session_dir()
        if not log_dir:
            return

        run_filename = os.path.join(log_dir, SESSION_LOG)

        config = cfgifc.open()
        filename = os.path.join(log_dir, 'config.yaml')
        with open(filename, "wt") as f:
            yaml.dump(config, f, indent=4, width=1024, default_flow_style=False)

        fmt = logging.Formatter(self.logformat, self.logdatefmt)
        handler = MyFileHandler(run_filename, filters=self.filters)
        handler.setFormatter(fmt)
        root_logger.addHandler(handler)

        STDOUT.info('Session path: %s', log_dir)
        session = cfgifc.get_session()
        url = session.get_url()
        if url:
            STDOUT.info('Session URL: %s', url)

    def _get_or_create_dirs(self, name, root=None):
        if root is None:
            root = self._get_session_dir()

        path = os.path.join(root, name)
        if not os.path.exists(path):
            oldumask = os.umask(0)
            os.makedirs(path)
            os.umask(oldumask)

        return path

    def _collect_forensics(self, test, err):
        """Collects screenshots and logs."""
        from ...interfaces.selenium import SeleniumInterface
        from ...interfaces.ssh import SSHInterface
        from ...interfaces.subprocess import ShellInterface
        from ...interfaces.icontrol import IcontrolInterface
        from ...interfaces.icontrol.em import EMInterface
        from ...interfaces.rest import RestInterface
        from ...interfaces.config import ConfigInterface
        from ...interfaces.testcase import (InterfaceHelper,
                                            INTERFACES_CONTAINER,
                                            LOGCOLLECT_CONTAINER)
        from ...base import TestCase, Interface
        from selenium.common.exceptions import WebDriverException

        if isinstance(test, Test) and isinstance(test.test, TestCase):
            test_name = test.id()

            # XXX: Dig into traceback to a *known* location to get the real
            # context. This is a limitation of nose in a way that it passes the
            # test file context instead of the failed ancestor context. This
            # occurs when setup_module() throws an exception.
            try:
                context = err[2].tb_next.tb_next.tb_frame.f_locals.get('context')
                # Error happened inside a setup_module
                if ismodule(context):
                    if getattr(context, '_logcollect_done', False):
                        return
                    test_name = context.__name__
                    context._logcollect_done = True
                # Error happened inside a setup_class
                elif isclass(context):
                    if getattr(context, '_logcollect_done', False):
                        return
                    test_name = "%s.%s" % (context.__module__, context.__name__)
                    # Avoid double passes
                    context._logcollect_done = True
            except:
                pass

            ih = InterfaceHelper()
            ih._setup(test_name)
            interfaces = ih.get_container(container=INTERFACES_CONTAINER).values()
            extra_files = ih.get_container(container=LOGCOLLECT_CONTAINER)
        else:
            return

        # Disregard skipped tests
        if issubclass(err[0], SkipTest):
            return

        config = self.context.get_config().open()
        if config is None:
            LOG.warn('config not available')
            return

        if not config.paths or not config.paths.logs:
            LOG.warn('logs path not defined')
            return

        # Save the test log
        LOG.debug('Collecting logs...')
        test_root = self._get_or_create_dirs(test_name)
        records = self.formatLogRecords()
        filename = os.path.join(test_root, TEST_LOG)
        if records:
            # I wish there was a better way to dump a whole "attr container",
            # but the attr plugin mixes the attrs with the test object attrs.
            test_meta = ["%s: %s" % (k, getattr(test.test, k, None))
                         for k in INC_TEST_ATTRIBUTES]
            with open(filename, "wt") as f:
                f.write('\n'.join(records))
                f.write('\n\n')

                f.write("Test attributes:\n")
                f.write('\n'.join(test_meta))
                f.write('\n\n')

                f.write(''.join(traceback.format_exception(*err)))

        # Sort interfaces by priority.
        interfaces.sort(key=lambda x: x._priority if hasattr(x, '_priority')
                        else 0)

        # Tests may define extra files to be picked up by the logcollect plugin
        # in case of a failure.
        for local_name, item in extra_files.iteritems():
            if isinstance(item, tuple):
                ifc, src = item
                assert isinstance(ifc, (SSHInterface, ShellInterface))
            else:
                ifc = ShellInterface()
                src = item

            was_opened = ifc.is_opened()
            if not was_opened:
                ifc.open()

            try:
                ifc.api.get(src, os.path.join(test_root, local_name))
            except IOError, e:
                LOG.error("Could not copy file '%s' (%s)", src, e)
            finally:
                if not was_opened:
                    ifc.close()

        if issubclass(err[0], WebDriverException) and err[1].screen:
            filename = os.path.join(test_root, 'screenshot.png')
            with codecs.open(filename, "w") as f:
                f.write(base64.b64decode(err[1].screen.encode('ascii')))

        visited = dict(ssh=set(), selenium=set())
        # Collect interface logs
        for interface in interfaces:
            if not isinstance(interface, Interface):
                continue

            if isinstance(interface, ConfigInterface):
                continue

            if not interface.is_opened():
                continue

            sshifcs = []
            if isinstance(interface, SeleniumInterface):
                try:
                    for window in interface.api.window_handles:
                        credentials = interface.get_credentials(window)

                        if credentials.device:
                            address = credentials.device.get_address()
                        else:
                            address = credentials.address or window

                        if address not in visited['selenium']:
                            log_root = self._get_or_create_dirs(address, test_root)
                            try:
                                self.UI.common.screen_shot(log_root, window=window,
                                                           ifc=interface)
                            except Exception, e:
                                LOG.error('Screenshot faied: %s', e)

                            if credentials.device:
                                sshifcs.append(SSHInterface(device=credentials.device))
                except:
                    err = sys.exc_info()
                    tb = ''.join(traceback.format_exception(*err))
                    LOG.debug('Error taking screenshot. (%s)', tb)
                finally:
                    try:
                        interface.api.switch_to_window('')
                    except:
                        LOG.debug('Error switching to main window.')

            elif isinstance(interface, SSHInterface):
                sshifcs.append(SSHInterface(device=interface.device))

            elif isinstance(interface, (IcontrolInterface, EMInterface,
                                        RestInterface)):
                if interface.device:
                    sshifcs.append(SSHInterface(device=interface.device))

            else:
                LOG.debug('Skip collection from interface: %s', interface)

            for sshifc in sshifcs:
                try:
                    with sshifc:
                        address = sshifc.address
                        if address not in visited['ssh']:
                            log_root = self._get_or_create_dirs(address, test_root)
                            LOG.debug('Collecting logs from %s', address)
                            try:
                                version = self.SSH.get_version(ifc=sshifc)
                                self.SSH.collect_logs(log_root, ifc=sshifc,
                                                      version=version)
                            except Exception, e:
                                LOG.error('Collecting logs failed: %s', e)
                            visited['ssh'].add(address)
                except:
                    err = sys.exc_info()
                    tb = ''.join(traceback.format_exception(*err))
                    LOG.debug('Error collecting logs. (%s)', tb)

        del interfaces[:]

    def handleFailure(self, test, err):
        try:
            self._collect_forensics(test, err)
        except Exception, e:
            LOG.critical('BUG: Uncaught exception in logcollect! %s', e)

    def handleError(self, test, err):
        try:
            self._collect_forensics(test, err)
        except Exception, e:
            LOG.critical('BUG: Uncaught exception in logcollect! %s', e)

    # These are needed to override LogCapture's behavior
    def formatError(self, test, err):
        return err

    def formatFailure(self, test, err):
        return err

    def beforeTest(self, test):
        """Clear buffers and handlers before test.
        """
        self.handler.truncate()

    def afterTest(self, test):
        pass

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
        self.context.teardown()
