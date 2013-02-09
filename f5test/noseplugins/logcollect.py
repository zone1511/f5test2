"""
This plugin collects logs from all devices used during a failed/errored test.
"""
from inspect import ismodule, isclass
from nose.case import Test
from nose.plugins.logcapture import LogCapture, MyMemoryHandler
import logging
import os
import sys
import threading
import traceback
import yaml

LOG = logging.getLogger(__name__)
STDOUT = logging.getLogger('stdout')
CONSOLE_LOG = 'console.log'
SESSION_LOG = 'session.log'
TEST_LOG = 'test.log'


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


class LogCollect(LogCapture):
    """
    Log Collector plugin. Enabled by default. Disable with ``--no-logcollect``.
    Upon a test failure this plugin iterates through each open interface and
    tries to collect troubleshooting data, like screenshots and log files.
    """
    enabled = True
    name = 'logcollect'
    score = 540
    logformat = '%(asctime)s - %(levelname)8s [%(threadName)s] %(name)s:%(lineno)d - %(message)s'

    def options(self, parser, env):
        """
        Add my options to command line.
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
        from ..interfaces.config import ConfigInterface
        import f5test.commands.ui as UI
        import f5test.commands.shell.ssh as SSH
        self.UI = UI
        self.SSH = SSH

        if not self.can_configure:
            return
        self.conf = conf
        disable = getattr(options, 'no_logcollect', False)
        if disable:
            self.enabled = False

        self.handler = MyMemoryHandler(1000, self.logformat, self.logdatefmt,
                                       self.filters)
        self.cfgifc = ConfigInterface()

    def _get_session_dir(self):
        path = self.cfgifc.get_session().path

        if path and not os.path.exists(path):
            oldumask = os.umask(0)
            os.makedirs(path)
            os.umask(oldumask)

        return path

    def setOutputStream(self, stream):
        if not self.conf.options.console_redirect:
            return

        logger = logging.getLogger('_console_')
        logger.propagate = False
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

    def begin(self):
        # setup our handler with root logger
        self.start()
        root_logger = logging.getLogger()

        log_dir = self._get_session_dir()
        if not log_dir:
            return

        run_filename = os.path.join(log_dir, SESSION_LOG)

        config = self.cfgifc.open()
        filename = os.path.join(log_dir, 'config.yaml')
        with open(filename, "wt") as f:
            yaml.dump(config, f, indent=4, default_flow_style=False)

        fmt = logging.Formatter(self.logformat, self.logdatefmt)
        handler = logging.FileHandler(run_filename)
        handler.setFormatter(fmt)
        root_logger.addHandler(handler)

        STDOUT.info('Session path: %s', log_dir)
        session = self.cfgifc.get_session()
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
        from ..interfaces.selenium import SeleniumInterface
        from ..interfaces.ssh import SSHInterface
        from ..interfaces.subprocess import ShellInterface
        from ..interfaces.icontrol import IcontrolInterface
        from ..interfaces.icontrol.em import EMInterface
        from ..interfaces.rest import RestInterface
        from ..interfaces.config import ConfigInterface
        from ..interfaces.testcase import (InterfaceHelper,
                                                INTERFACES_CONTAINER,
                                                LOGCOLLECT_CONTAINER)
        from ..base import TestCase, Interface

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

        config = self.cfgifc.open()
        if config is None:
            LOG.warn('config not available')
            return

        if not config.paths or not config.paths.logs:
            LOG.warn('logs path not defined')
            return

        # Save the test log
        test_root = self._get_or_create_dirs(test_name)
        records = self.formatLogRecords()
        filename = os.path.join(test_root, TEST_LOG)
        if records:
            with open(filename, "wt") as f:
                f.write('\n'.join(records))
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
        pass

    def formatFailure(self, test, err):
        pass

    def beforeTest(self, test):
        """Clear buffers and handlers before test.
        """
        self.handler.truncate()

    def afterTest(self, test):
        pass

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
