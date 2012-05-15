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

LOG = logging.getLogger(__name__)


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
        self.buffer = []
        #self.write('\n') # text-mode streams translate to \r\n if needed

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
    Plugin that installs a SKIP error class for the SkipTest
    exception.  When SkipTest is raised, the exception will be logged
    in the skipped attribute of the result, 'S' or 'SKIP' (verbose)
    will be output, and the exception will not be counted as an error
    or failure.
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

    def _get_session_dir(self):
        from f5test.interfaces.config import ConfigInterface

        cfgifc = ConfigInterface()
        path = cfgifc.get_session().path
        
        if not os.path.exists(path):
            oldumask = os.umask(0)
            os.makedirs(path)
            os.umask(oldumask)
        
        return path

    def setOutputStream(self, stream):
        if not self.conf.options.console_redirect:
            return

        logger = logging.getLogger('_console_')
        logger.propagate = False

        log_dir = self._get_session_dir()
        console_filename = os.path.join(log_dir, 'console.log')

        logformat = '%(asctime)s - %(message)s'
        fmt = logging.Formatter(logformat, self.logdatefmt)
        handler = logging.FileHandler(console_filename)
        handler.setFormatter(fmt)
        logger.addHandler(handler)

        proxy = LoggingProxy(logger)
        return proxy

    def begin(self):
        # setup our handler with root logger
        root_logger = logging.getLogger()

        log_dir = self._get_session_dir()
        run_filename = os.path.join(log_dir, 'run.log')

        fmt = logging.Formatter(self.logformat, self.logdatefmt)
        handler = logging.FileHandler(run_filename)
        handler.setFormatter(fmt)
        root_logger.addHandler(handler)
        
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
        from f5test.interfaces.selenium import SeleniumInterface
        from f5test.interfaces.ssh import SSHInterface
        from f5test.interfaces.icontrol import IcontrolInterface
        from f5test.interfaces.icontrol.em import EMInterface
        from f5test.interfaces.rest import RestInterface
        from f5test.interfaces.config import ConfigInterface
        from f5test.base import TestCase, Interface

        if isinstance(test, Test) and isinstance(test.test, TestCase):
            test_name = test.id()
            
            # XXX: Dig into traceback to a *known* location to get the real
            # context. This is a limitation of nose in a way that it passes the
            # test file context instead of the failed ancestor context. This
            # occurs when setup_module() throws an exception.
            try:
                interfaces = None
                context = err[2].tb_next.tb_next.tb_frame.f_locals.get('context')
                # Error happened inside a setup_module
                if ismodule(context):
                    if getattr(context, '_logcollect_done', False):
                        return
                    test_name = context.__name__
                    interfaces = getattr(context, '_IFCS', [])
                    context._logcollect_done = True
                # Error happened inside a setup_class
                elif isclass(context):
                    if getattr(context, '_logcollect_done', False):
                        return
                    test_name = "%s.%s" % (context.__module__, context.__name__)
                    if hasattr(context, 'ih'):
                        interfaces = context.ih._apis.keys()
                    # Avoid double passes
                    context._logcollect_done = True
            except:
                pass

            if not interfaces:
                if not hasattr(test.test, '_apis'):
                    return
                interfaces = test.test._apis.keys()
        else:
            return
        
        config = ConfigInterface().open()
        if config is None:
            LOG.warn('config not available')
            return

        if not config.paths or not config.paths.logs:
            LOG.warn('logs path not defined')
            return

        # Save the test log
        test_root = self._get_or_create_dirs(test_name)
        records = self.formatLogRecords()
        filename = os.path.join(test_root, 'test.log')
        if records:
            with open(filename, "wt") as f:
                f.write('\n'.join(records))

        # Sort interfaces by priority.
        interfaces.sort(key=lambda x:x._priority if hasattr(x, '_priority') 
                                     else 0)

        visited = dict(ssh=set(), selenium=set())
        # Collect interface logs
        for interface in interfaces:
            if not isinstance(interface, Interface):
                continue

            if isinstance(interface, ConfigInterface):
                continue

            sshifcs = []
            
            if isinstance(interface, SeleniumInterface):
                if not interface.is_opened():
                    LOG.warning('Unopened selennium interface: %s', interface)
                    continue
                
                try:
                    for window in interface.api.window_handles:
                        credentials = interface.get_credentials(window)
                        
                        if credentials.device:
                            address = credentials.device.get_address()
                        else:
                            address = credentials.address or window
    
                        if address not in visited['selenium']:
                            log_root = self._get_or_create_dirs(address, test_root)
        
                            LOG.warning('Dumping screenshot for: %s (%s)', address, 
                                        window)
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
        self._collect_forensics(test, err)

    def handleError(self, test, err):
        self._collect_forensics(test, err)

    # These are needed to override LogCapture's behavior
    def formatError(self, test, err):
        pass

    def formatFailure(self, test, err):
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
