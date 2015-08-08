'''
Created on Aug 28, 2014

@author: jono
'''
import logging
import os
import re
from threading import Thread
from nose.case import Test
import time

from f5test.interfaces.ssh.core import SSHInterface
from f5test.interfaces.ssh.driver import SSHTimeoutError
from f5test.interfaces.subprocess.core import ShellInterface
from f5test.interfaces.testcase import ContextHelper
import f5test.commands.shell as SCMD
from ...base import enum
from ...macros.tmosconf.placer import SCF_FILENAME

from . import ExtendedPlugin, PLUGIN_NAME


LOG = logging.getLogger(__name__)
QKVIEWS_DIR = 'qkviews'
CORES_DIR = 'cores'
TESTCASE_FLAG = 'qkview_on_fail'
QKVIEW = enum('ALWAYS', 'ON_FAIL', 'NEVER')
TIMEOUT = 300


class CollectQkviewOnFail(object):
    pass


class CoreCollector(Thread):

    def __init__(self, sshifc, data, mode, root=None):
        super(CoreCollector, self).__init__(name='CoreCollector@%s' % sshifc.address)
        self.sshifc = sshifc
        self.data = data
        self.mode = mode
        self.root = root

        self.context = ContextHelper(__name__)
        self.session = self.context.get_config().get_session()

    def _get_session_dir(self):
        path = self.session.path

        if path and not os.path.exists(path):
            oldumask = os.umask(0)
            os.makedirs(path)
            os.umask(oldumask)

        return path

    def _get_or_create_dirs(self, name, root=None):
        if root is None:
            root = self._get_session_dir()
        else:
            if not os.path.isdir(root):
                root = os.path.join(self._get_session_dir(), root)

        created = False
        path = os.path.join(root, name)

        # Windows-based NAS doesn't support :'s in names
        path = path.replace(':', '@')
        if not os.path.exists(path):
            oldumask = os.umask(0)
            os.makedirs(path)
            os.umask(oldumask)
            created = True

        return path, created

    def run(self):
        LOG.info('Looking for cores...')
        d = self.data.cores
        d.data = {}
        d.checked = time.time()

        with self.sshifc as sshifc:
            if SCMD.ssh.cores_exist(ifc=sshifc):
                LOG.info('Cores found!')
                cores_dir, _ = self._get_or_create_dirs("%s/%s" % (CORES_DIR, sshifc.address),
                                                        self.root)

                SCMD.ssh.scp_get(ifc=sshifc, source='/var/core/*',
                                 destination=cores_dir)
                sshifc.api.run('rm -f /var/core/*')

                # Add read permissions to group and others.
                with ShellInterface(shell=True) as shell:
                    shell.api.run('chmod -R go+r %s' % cores_dir)
                if sshifc.device:
                    d.data[sshifc.device.get_alias()] = True

            if self.mode == QKVIEW.ALWAYS or \
               (self.mode == QKVIEW.ON_FAIL and self.data.test_result and
                    not self.data.test_result.wasSuccessful()):
                try:
                    LOG.info("Generating qkview...")
                    ret = SCMD.ssh.generic('qkview', ifc=sshifc)
                    name = re.search('^/var/.+$', ret.stderr, flags=re.M).group(0)

                    LOG.info("Downloading qkview...")
                    qk_dir, _ = self._get_or_create_dirs("%s/%s" % (QKVIEWS_DIR, sshifc.address),
                                                         self.root)

                    SCMD.ssh.scp_get(ifc=sshifc, source=name, destination=qk_dir)
                    if sshifc.api.exists(SCF_FILENAME):
                        SCMD.ssh.scp_get(ifc=sshifc, source=SCF_FILENAME,
                                         destination=qk_dir)

                except SSHTimeoutError:
                    LOG.warning('Could not complete qkview on %s', sshifc.address)


class Cores(ExtendedPlugin):
    """
    Look for and collect core and qkview files.
    """
    enabled = True
    score = 501  # Needs to be higher than the other report plugins that depend on it

    def options(self, parser, env):
        """Register commandline options."""
        parser.add_option('--with-qkview', action='store',
                          dest='with_qkview', default=QKVIEW.ON_FAIL,
                          help="Enable qkview collecting. (default: on failure)")

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """
        super(Cores, self).configure(options, noseconfig)
        self.data = ContextHelper().set_container(PLUGIN_NAME)
        self.enabled = not(noseconfig.options.with_qkview.upper() == QKVIEW.NEVER)

        # There's really no point in collecting just quickviews without other logs
        # For now, disable this plugin if --no-logcollect is present.
        self.enabled = self.enabled and not(noseconfig.options.no_logcollect)

        self.data.cores = {}
        self.blocked_contexts = {}

    def _collect_forensics(self, test, err, context=None):
        from ...interfaces.testcase import (InterfaceHelper,
                                            INTERFACES_CONTAINER)

        if context:
            blocked_tests = self.blocked_contexts.setdefault(context, [])
            test_name = context.id()

            # print (test, err, context)
            # We already collected logs for this context
            if blocked_tests:
                return

            blocked_tests.append((test, err))
        else:
            test_name = test.id()

        ih = InterfaceHelper()
        ih._setup(test_name)
        interfaces = ih.get_container(container=INTERFACES_CONTAINER).values()

        #if not getattr(test.test, TESTCASE_FLAG, False):
        if not (isinstance(test, Test) and isinstance(test.test, CollectQkviewOnFail)):
            return

        sshifcs = []
        for interface in interfaces:
            if isinstance(interface, SSHInterface):
                sshifcs.append(SSHInterface(device=interface.device,
                                            address=interface.address,
                                            username=interface.username,
                                            password=interface.password,
                                            key_filename=interface.key_filename))

        pool = []
        for sshifc in sshifcs:
            t = CoreCollector(sshifc, self.data,
                              self.noseconfig.options.with_qkview.upper(),
                              test_name)
            t.start()
            pool.append(t)

        for t in pool:
            t.join(TIMEOUT + 10)

    def handleFailure(self, test, err):
        try:
            self._collect_forensics(test, err)
        except Exception, e:
            LOG.critical('BUG: Uncaught exception in %s! %s', self.name, e)

    def handleError(self, test, err):
        try:
            self._collect_forensics(test, err)
        except Exception, e:
            LOG.critical('BUG: Uncaught exception in %s! %s', self.name, e)

    def handleBlocked(self, test, err, context):
        try:
            self._collect_forensics(test, err, context)
        except Exception, e:
            LOG.critical('BUG: Uncaught exception in %s! %s', self.name, e)

    def finalize(self, result):
        pool = []
        # This flag is set by atom plugin in begin()
        if result.failfast:
            return

        for dut in self.data.duts:
            sshifc = SSHInterface(device=dut.device, timeout=TIMEOUT)
            t = CoreCollector(sshifc, self.data,
                              self.noseconfig.options.with_qkview.upper())
            t.start()
            pool.append(t)

        for t in pool:
            t.join(TIMEOUT + 10)
