'''
Created on Aug 28, 2014

@author: jono
'''
import logging
import os
import re
from threading import Thread
import time

from f5test.interfaces.config.core import ConfigInterface
from f5test.interfaces.ssh.core import SSHInterface
from f5test.interfaces.ssh.driver import SSHTimeoutError
from f5test.interfaces.subprocess.core import ShellInterface
from f5test.interfaces.testcase import ContextHelper
import f5test.commands.shell as SCMD
from ...base import enum

from . import ExtendedPlugin, PLUGIN_NAME


LOG = logging.getLogger(__name__)
QKVIEWS_DIR = 'qkviews'
QKVIEW = enum('ALWAYS', 'ON_FAIL', 'NEVER')


class CoreCollector(Thread):

    def __init__(self, device, data, mode):
        super(CoreCollector, self).__init__(name='CoreCollector@%s' % device)
        self.device = device
        self.data = data
        self.session = ConfigInterface().get_session()
        self.mode = mode

    def run(self):
        LOG.info('Looking for cores...')
        d = self.data.cores
        d.data = {}
        d.checked = time.time()

        with SSHInterface(device=self.device, timeout=300) as sshifc:
            if SCMD.ssh.cores_exist(ifc=sshifc):
                LOG.info('Cores found!')
                cores_dir = os.path.join(self.session.path, 'cores',
                                         self.device.get_address())
                cores_dir = os.path.expanduser(cores_dir)
                cores_dir = os.path.expandvars(cores_dir)
                if not os.path.exists(cores_dir):
                    os.makedirs(cores_dir)

                SCMD.ssh.scp_get(ifc=sshifc, source='/var/core/*',
                                 destination=cores_dir, nokex=True)
                sshifc.api.run('rm -f /var/core/*')

                # Add read permissions to group and others.
                with ShellInterface(shell=True) as shell:
                    shell.api.run('chmod -R go+r %s' % cores_dir)
                d.data[self.device.get_alias()] = True

            if self.mode == QKVIEW.ALWAYS or \
               (self.mode == QKVIEW.ON_FAIL and self.data.test_result and
                    not self.data.test_result.wasSuccessful()):
                try:
                    LOG.info("Generating qkview...")
                    ret = SCMD.ssh.generic('qkview', ifc=sshifc)
                    name = re.search('^/var/.+$', ret.stderr, flags=re.M).group(0)

                    LOG.info("Downloading qkview...")
                    qk_dir = os.path.join(self.session.path, QKVIEWS_DIR,
                                          self.device.get_address())
                    qk_dir = os.path.expanduser(qk_dir)
                    qk_dir = os.path.expandvars(qk_dir)
                    if not os.path.exists(qk_dir):
                        os.makedirs(qk_dir)

                    SCMD.ssh.scp_get(ifc=sshifc, source=name, destination=qk_dir,
                                     nokex=True)
                except SSHTimeoutError:
                    LOG.warning('Could not complete qkview on %s', self.device)


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
        self.data.cores = {}

    def finalize(self, result):
        pool = []
        for dut in self.data.duts:
            t = CoreCollector(dut.device, self.data,
                              self.noseconfig.options.with_qkview.upper())
            t.start()
            pool.append(t)

        for t in pool:
            t.join()
